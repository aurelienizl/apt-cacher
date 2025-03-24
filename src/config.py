#!/usr/bin/env python3
"""
@file config.py
@brief Configuration settings for the proxy server.
"""

# Server port number
PORT = 3142

# SQLite database file name for persistent caching
DB_NAME = "cache.db"

# Cache expiration time in seconds (30 days)
CACHE_EXPIRATION_SECONDS = 2592000

# Maximum number of concurrent client connections
MAX_CONCURRENT_CONNECTIONS = 100

# Batch settings for write operations to the database
BATCH_SIZE = 10          # Maximum number of write operations per batch
BATCH_INTERVAL = 1.0     # Maximum wait time (in seconds) before committing a batch
