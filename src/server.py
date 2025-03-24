#!/usr/bin/env python3
"""
@file main.py
@brief Entry point for the proxy server application.
"""

import asyncio
import aiohttp
from config import PORT, MAX_CONCURRENT_CONNECTIONS
from db import CacheDatabase
from memory_cache import MemoryCache
from handler import ProxyHandler
from logger import logger

# Semaphore to limit the number of concurrent client connections.
semaphore = asyncio.Semaphore(MAX_CONCURRENT_CONNECTIONS)

async def limited_handle_client(reader, writer, proxy_handler):
    """
    @brief Wrapper to handle a client connection with concurrency control.
    @param reader The client's stream reader.
    @param writer The client's stream writer.
    @param proxy_handler An instance of ProxyHandler.
    """
    async with semaphore:
        await proxy_handler.handle_client(reader, writer)

async def main():
    """
    @brief Initialize resources and start the proxy server.
    
    This function sets up the persistent and in-memory caches, creates an aiohttp session,
    and starts the asyncio server to handle incoming connections.
    """
    db = CacheDatabase()
    await db.init()
    mem_cache = MemoryCache()
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_CONNECTIONS)
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        proxy_handler = ProxyHandler(session, db, mem_cache)
        server = await asyncio.start_server(
            lambda r, w: limited_handle_client(r, w, proxy_handler), '0.0.0.0', PORT
        )
        logger.info(f"Server running on port {PORT}")
        async with server:
            try:
                await server.serve_forever()
            except asyncio.CancelledError:
                pass
    await db.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down.")
