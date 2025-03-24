#!/usr/bin/env python3
import os

"""
@file config.py
@brief Configuration settings for the proxy server.
"""

PORT = int(os.getenv("PORT", 3142))
DB_NAME = os.getenv("DB_NAME", "/app/data/cache.db")
CACHE_EXPIRATION_SECONDS = int(os.getenv("CACHE_EXPIRATION_SECONDS", 2592000))
MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS", 100))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
BATCH_INTERVAL = float(os.getenv("BATCH_INTERVAL", 1.0))