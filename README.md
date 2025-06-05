# Amazon Book Image API

A service that extracts high-resolution book cover images from Amazon book pages.

## Features

- Extract book cover images from Amazon product pages
- Redis caching with configurable timeout
- File-based cache fallback
- Docker support for easy deployment
- Configurable via environment variables

## API Endpoints

### GET /book-image

Extract a book cover image from an Amazon book URL.

**Parameters:**

- `book_url` (required): The Amazon book URL
- `debug` (optional): Enable debug mode (true/false)
- `profile` (optional): Enable profiling (true/false)

**Example Request:**

```http
GET /book-image?book_url=https://www.amazon.com/dp/B00BD1Q0IQ
```

**Example Response:**

```json
{
  "success": true,
  "image_url": "https://m.media-amazon.com/images/I/51Ga5GuElyL._SL1000_.jpg",
  "book_url": "https://www.amazon.com/dp/B00BD1Q0IQ",
  "processing_time_seconds": 0.123,
  "cached": true,
  "cache_backend": "redis"
}
```

## Installation

### Using Docker (Recommended)

1. Clone the repository
2. Configure environment variables in `.env` file
3. Build and run with Docker Compose:

```bash
docker compose up -d
```

### Manual Installation

1. Clone the repository
2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Configure environment variables in `.env` file
2. Run the application:

```bash
gunicorn wsgi:app --bind 0.0.0.0:8080 --workers 2 --timeout 60
```

## Configuration

Configuration is managed through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `CACHE_REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `CACHE_TIMEOUT` | Cache timeout in seconds | `31536000` (1 year) |
| `CACHE_KEY_PREFIX` | Prefix for cache keys | `amazon_book_image` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `FLASK_ENV` | Flask environment | `production` |

## Cache Configuration

The application supports two caching backends:

1. **Redis** (preferred): Used when `CACHE_REDIS_URL` is set and not empty
2. **File-based**: Used as fallback when Redis is unavailable

## Docker Support

The application includes Docker support for easy deployment:

- `Dockerfile`: Defines the container image
- `docker-compose.yml`: Orchestrates the application and Redis services

To run with Docker:

```bash
# Build and start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## License

MIT
