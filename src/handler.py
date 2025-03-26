#!/usr/bin/env python3
"""
@file handler.py
@brief Handles incoming client connections and proxying of HTTP requests.
"""

import asyncio
import aiohttp
import socket  # Required for setting socket options.
from logger import logger


class ProxyHandler:
    """
    @brief Encapsulates the logic to process client requests, perform caching,
           and forward responses between the client and target server.
    """

    def __init__(self, session, db, memory_cache):
        """
        @brief Initialize the ProxyHandler.
        @param session The aiohttp client session used to make outgoing HTTP requests.
        @param db The CacheDatabase instance for persistent caching.
        @param memory_cache The MemoryCache instance for in-memory caching.
        """
        self.session = session
        self.db = db
        self.memory_cache = memory_cache

    async def forward(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        @brief Forward data between a reader and writer stream.
        @param reader The source stream.
        @param writer The destination stream.
        """
        try:
            while True:
                data = await reader.read(8192)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception as e:
            logger.error(f"Error forwarding data: {e}")

    async def fetch_and_forward(self, url, writer, cache_enabled=True):
        """
        @brief Fetch a remote URL and forward the response to the client.
        @param url The URL to fetch.
        @param writer The client's stream writer.
        @param cache_enabled Flag to enable caching of successful responses.
        """
        try:
            async with self.session.get(url) as resp:
                content = await resp.read()
                status = resp.status
                headers = dict(resp.headers)

                # Remove chunked transfer and set a proper Content-Length header.
                headers.pop("Transfer-Encoding", None)
                headers["Content-Length"] = str(len(content))

                # Write status line and headers to the client.
                response_line = f"HTTP/1.1 {status} {resp.reason}\r\n"
                writer.write(response_line.encode())
                for key, value in headers.items():
                    writer.write(f"{key}: {value}\r\n".encode())
                writer.write(b"\r\n")
                writer.write(content)
                await writer.drain()

                # Cache the response if enabled and successful.
                if cache_enabled and status == 200:
                    await self.db.cache_response(url, content, headers, status)
                    await self.memory_cache.set(
                        url,
                        {"content": content, "headers": headers, "status_code": status},
                    )
        except aiohttp.ClientError as e:
            error_response = f"HTTP/1.1 502 Bad Gateway\r\n\r\n{e}"
            writer.write(error_response.encode())
            await writer.drain()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def send_error(self, writer, status_code=400, reason="Bad Request"):
        """
        @brief Send an error response to the client.
        @param writer The client's stream writer.
        @param status_code HTTP status code.
        @param reason Reason phrase for the error.
        """
        response_line = f"HTTP/1.1 {status_code} {reason}\r\n\r\n"
        writer.write(response_line.encode())
        await writer.drain()
        writer.close()

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        @brief Process a client connection by parsing the HTTP request,
               checking caches, and forwarding the request appropriately.
        @param reader The client's stream reader.
        @param writer The client's stream writer.
        """
        sock = writer.get_extra_info("socket")
        if sock:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        try:
            # Read and parse the request line.
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return

            parts = request_line.decode().strip().split()
            if len(parts) < 3:
                raise ValueError("Incomplete request line")
            method, path, _ = parts
        except Exception:
            await self.send_error(writer)
            return

        # Read HTTP headers.
        headers = {}
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b""):
                break
            key, sep, value = line.decode().partition(":")
            if sep:
                headers[key.strip()] = value.strip()

        # Construct the full URL if needed.
        url = (
            path
            if path.startswith("http")
            else f"http://{headers.get('Host', '')}{path}"
        )

        if method.upper() == "CONNECT":
            logger.info(f"Establishing tunnel to {path}")
            try:
                host, port_str = path.split(":")
                port = int(port_str)
                remote_reader, remote_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=10
                )
            except Exception as e:
                logger.error(f"Error establishing tunnel: {e}")
                await self.send_error(writer, status_code=504, reason="Gateway Timeout")
                return

            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()

            # Create tasks for both directions.
            task1 = asyncio.create_task(self.forward(reader, remote_writer))
            task2 = asyncio.create_task(self.forward(remote_reader, writer))

            # Wait for either direction to finish.
            done, pending = await asyncio.wait(
                [task1, task2], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel any pending tasks.
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.error("Task cancelled")

            # Optionally close both writers.
            remote_writer.close()
            writer.close()
            try:
                await remote_writer.wait_closed()
                await writer.wait_closed()
            except Exception:
                logger.error("Error closing tunnel streams")
                
        elif method.upper() == "GET":
            # Try to retrieve from in-memory or persistent cache.
            cached = await self.memory_cache.get(url) or await self.db.get_cached(url)
            logger.info(f"Requesting {url}")
            if cached:
                logger.info(f"Cache hit for {url}")
                response_line = f"HTTP/1.1 {cached['status_code']} OK\r\n"
                writer.write(response_line.encode())
                for key, value in cached["headers"].items():
                    writer.write(f"{key}: {value}\r\n".encode())
                writer.write(b"\r\n")
                writer.write(cached["content"])
                await writer.drain()
                writer.close()
            else:
                logger.info(f"Cache miss for {url}")
                await self.fetch_and_forward(url, writer)
        else:
            await self.send_error(writer, status_code=405, reason="Method Not Allowed")
