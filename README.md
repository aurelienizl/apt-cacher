# Proxy Caching Server

A lightweight, asynchronous HTTP proxy caching server implemented in Python. This project uses persistent SQLite storage along with an in-memory TTL cache to efficiently cache and serve HTTP responses, reducing redundant network requests and improving response times.

## Features

- **Asynchronous I/O:** Built using Python's `asyncio` and `aiohttp` for efficient concurrent handling of client connections.
- **Persistent Caching:** Caches HTTP responses in an SQLite database with WAL mode enabled for better concurrency.
- **In-Memory Cache:** Uses an in-memory TTL cache via `cachetools` to serve frequent requests quickly.
- **Batch Write Operations:** Groups write operations to the database to minimize I/O overhead.
- **Configurable:** All key parameters (e.g., port number, cache expiration, maximum connections) can be easily configured in `src/config.py`.
- **Logging:** Detailed logging is available for debugging and monitoring via a configurable logger.

## Project Structure

```
.
├── Dockerfile
├── LICENSE
├── README.md
├── requirements.txt
└── src
    ├── config.py
    ├── db.py
    ├── handler.py
    ├── logger.py
    ├── memory_cache.py
    └── server.py
```

- **src/config.py:** Contains configuration parameters.
- **src/db.py:** Manages persistent caching with SQLite using asynchronous batch write operations.
- **src/handler.py:** Contains HTTP request handling and proxy logic.
- **src/logger.py:** Configures application logging.
- **src/memory_cache.py:** Implements an in-memory TTL cache.
- **src/server.py:** The entry point for the proxy server.

## Requirements

- Python 3.7+
- [aiosqlite](https://pypi.org/project/aiosqlite/)
- [aiohttp](https://pypi.org/project/aiohttp/)
- [cachetools](https://pypi.org/project/cachetools/)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/proxy-caching-server.git
   cd proxy-caching-server
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Running the Server Locally

To start the proxy caching server locally, run:

```bash
python src/server.py
```

The server listens on the port specified in `src/config.py` (default: 3142). Logs will be output to both the console and the `proxy.log` file.

## Docker Usage

This project is Dockerized to simplify deployment.

### Build the Docker Image

In the project root directory, run:

```bash
docker build -t proxy-caching-server:latest .
```

### Run the Docker Container

Run the container by mapping the container port to your host:

```bash
docker run -p 3142:3142 proxy-caching-server:latest
```

This maps port **3142** on your host to port **3142** in the container.

## Contributing

Contributions are welcome! Please open issues or submit pull requests to help improve the project.

## License

This project is licensed under the [MIT License](LICENSE).

## Release

This project is ready for release. Tag the release (e.g., **v1.0.0**) once you have thoroughly tested it in your environment.

## Acknowledgements

- Thanks to the developers of `asyncio`, `aiohttp`, and `aiosqlite` for providing robust asynchronous libraries.
- Special thanks to the maintainers of `cachetools` for a simple yet effective caching solution.
