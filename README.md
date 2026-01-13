# Lyftr AI — Backend Assignment

A production-style FastAPI service for message processing, featuring idempotent storage, HMAC validation, structured logging, and Prometheus metrics.

## 1. Project Overview
This service provides a robust backend for receiving message webhooks and retrieving them via a REST API. It is built with FastAPI and uses SQLite for persistent storage.

**Key Features:**
- **Idempotent Webhooks**: HMAC-SHA256 signature validation and deduplication.
- **Structured Logging**: Every request produces exactly one JSON log line to stdout.
- **Observability**: Prometheus-style metrics and health/readiness probes.
- **Persistence**: SQLite storage with parameterized queries (no ORM).

## 2. How to Run

### Prerequisites
- Docker and Docker Compose
- Make (optional, for convenience)

### Commands
```bash
# Start the service in detached mode
make up

# View structured JSON logs
make logs

# Stop and remove volumes
make down
```

### URLs
- **API**: `http://localhost:8000`
- **Health**: `http://localhost:8000/health/ready`
- **Metrics**: `http://localhost:8000/metrics`

## 3. API Usage Examples

### Webhook (POST)
Requires `X-Signature` header (HMAC-SHA256 of body using `WEBHOOK_SECRET`).
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: <hex_signature>" \
  -d '{
    "message_id": "msg_123",
    "from": "+1234567890",
    "to": "+0987654321",
    "ts": "2024-01-01T12:00:00Z",
    "text": "Hello World"
  }'
```

### Get Messages (GET)
Supports pagination and filtering (`from`, `since`, `q`).
```bash
curl "http://localhost:8000/messages?limit=10&q=Hello"
```

### Stats (GET)
```bash
curl http://localhost:8000/stats
```

## 4. Design Decisions
- **No ORM**: Used raw `sqlite3` with parameterized queries to ensure maximum control over performance and schema determinism.
- **Middleware Logging**: Implemented a custom middleware to ensure every request (including failures) is logged in a consistent JSON format with a unique `request_id`.
- **In-Memory Metrics**: Implemented a thread-safe metrics store without external dependencies to keep the deployment footprint minimal.
- **Multi-Stage Docker**: Used a builder stage to keep the final production image slim and secure.

## 5. Setup Used
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: SQLite
- **AI Tools**: This project was developed in collaboration with **Antigravity**, an AI coding assistant by Google DeepMind.
