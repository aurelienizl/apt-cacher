#!/usr/bin/env python3
"""
@file memory_cache.py
@brief In-memory caching module using TTLCache.
"""

import asyncio
from cachetools import TTLCache
from config import CACHE_EXPIRATION_SECONDS


class MemoryCache:
    """
    @brief Provides an asynchronous in-memory cache with time-to-live support.

    Uses cachetools.TTLCache and an asyncio lock to protect concurrent access.
    """

    def __init__(self, maxsize=1000, ttl=CACHE_EXPIRATION_SECONDS):
        """
        @brief Initialize the MemoryCache.
        @param maxsize Maximum number of items in the cache.
        @param ttl Time-to-live (in seconds) for each cached item.
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.lock = asyncio.Lock()

    async def get(self, url: str):
        """
        @brief Retrieve a cached response for the given URL.
        @param url The URL key to look up.
        @return The cached response or None if not found.
        """
        async with self.lock:
            return self.cache.get(url)

    async def set(self, url: str, response: dict):
        """
        @brief Set a cached response for the given URL.
        @param url The URL key.
        @param response The response data to cache.
        """
        async with self.lock:
            self.cache[url] = response
