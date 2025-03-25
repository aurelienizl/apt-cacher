#!/usr/bin/env python3
"""
@file logger.py
@brief Logging configuration for the proxy server.
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("proxy.log"), logging.StreamHandler()],
)
logger = logging.getLogger("proxy_server")
