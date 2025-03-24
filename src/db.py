#!/usr/bin/env python3
"""
@file db.py
@brief Database module for handling persistent cache using SQLite.
"""

import aiosqlite
import asyncio
import json
from datetime import datetime, timedelta
from config import DB_NAME, CACHE_EXPIRATION_SECONDS, BATCH_SIZE, BATCH_INTERVAL

class CacheDatabase:
    """
    @brief Encapsulates the SQLite database operations for caching.
    
    Provides methods to initialize the database, verify data integrity,
    perform batch writes, query cached responses, and shut down the database.
    """
    def __init__(self, db_name=DB_NAME):
        """
        @brief Initialize the CacheDatabase instance.
        @param db_name Database file name.
        """
        self.db_name = db_name
        self.conn = None
        self.lock = asyncio.Lock()
        self.write_queue = asyncio.Queue()
        self.worker_task = None

    async def init(self):
        """
        @brief Initialize the database connection, create table if needed,
               verify integrity, and start the background write worker.
        """
        self.conn = await aiosqlite.connect(self.db_name)
        await self.conn.execute('PRAGMA journal_mode=WAL;')
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                url TEXT PRIMARY KEY,
                content BLOB,
                headers TEXT,
                status_code INTEGER,
                expected_size INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self.conn.commit()
        await self.verify_integrity()
        self.worker_task = asyncio.create_task(self._write_worker())

    async def verify_integrity(self):
        """
        @brief Verify the database integrity and remove corrupted cache entries.
        
        Corrupted entries are defined as those where the stored content length
        does not match the expected size.
        """
        async with self.lock:
            async with self.conn.execute("PRAGMA integrity_check;") as cursor:
                result = await cursor.fetchone()
                if result[0] != "ok":
                    raise Exception("Database integrity check failed: " + result[0])
            async with self.conn.execute("SELECT url, LENGTH(content), expected_size FROM cache") as cursor:
                async for row in cursor:
                    url, actual_size, expected_size = row
                    if expected_size is not None and actual_size != expected_size:
                        await self.conn.execute("DELETE FROM cache WHERE url = ?", (url,))
            await self.conn.commit()

    async def _write_worker(self):
        """
        @brief Background worker that batches and writes cache responses to the database.
        
        Items are taken from a queue and committed in batches to reduce I/O overhead.
        """
        while True:
            try:
                batch = []
                try:
                    # Wait up to BATCH_INTERVAL for the first item
                    item = await asyncio.wait_for(self.write_queue.get(), timeout=BATCH_INTERVAL)
                    batch.append(item)
                    for _ in range(BATCH_SIZE - 1):
                        try:
                            item = self.write_queue.get_nowait()
                            batch.append(item)
                        except asyncio.QueueEmpty:
                            break
                except asyncio.TimeoutError:
                    if not batch:
                        continue

                if batch:
                    # Format current time to match SQLite's DEFAULT CURRENT_TIMESTAMP format
                    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    values = [
                        (url, content, json.dumps(headers), status_code, expected_size, current_time)
                        for url, content, headers, status_code, expected_size in batch
                    ]
                    async with self.lock:
                        try:
                            await self.conn.execute("BEGIN")
                            await self.conn.executemany(
                                "INSERT OR REPLACE INTO cache (url, content, headers, status_code, expected_size, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                                values
                            )
                            await self.conn.commit()
                        except Exception as e:
                            await self.conn.rollback()
                    for _ in batch:
                        self.write_queue.task_done()
            except Exception as e:
                # Simple error logging; for production integrate with a proper logging system.
                print(f"Error in write worker: {e}")

    async def get_cached(self, url: str):
        """
        @brief Retrieve a cached response for the given URL if it is not expired.
        @param url The URL for which to retrieve the cached response.
        @return A dictionary with 'content', 'headers', and 'status_code' if found, otherwise None.
        """
        expiration = (datetime.utcnow() - timedelta(seconds=CACHE_EXPIRATION_SECONDS)).strftime("%Y-%m-%d %H:%M:%S")
        async with self.lock:
            async with self.conn.execute(
                "SELECT content, headers, status_code FROM cache WHERE url = ? AND timestamp > ?",
                (url, expiration)
            ) as cursor:
                row = await cursor.fetchone()
        if row:
            content, headers_json, status_code = row
            return {"content": content, "headers": json.loads(headers_json), "status_code": status_code}
        return None

    async def cache_response(self, url: str, content: bytes, headers: dict, status_code: int):
        """
        @brief Enqueue a cache write operation.
        @param url The URL associated with the response.
        @param content The response content as bytes.
        @param headers The response headers as a dictionary.
        @param status_code The HTTP status code of the response.
        """
        expected_size = int(headers.get("Content-Length", len(content)))
        await self.write_queue.put((url, content, headers, status_code, expected_size))

    async def get_total_size(self):
        """
        @brief Calculate the total size in bytes of all cached content.
        @return Total size in bytes.
        """
        async with self.lock:
            async with self.conn.execute("SELECT SUM(LENGTH(content)) FROM cache") as cursor:
                row = await cursor.fetchone()
                return row[0] or 0

    async def shutdown(self):
        """
        @brief Shutdown the database by finishing pending writes and closing the connection.
        """
        await self.write_queue.join()
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        if self.conn:
            await self.conn.close()
