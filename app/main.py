import hmac
import hashlib
import uuid
import time
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, ValidationError
from .models import init_db, check_db
from .config import config
from .storage import insert_message, fetch_messages, get_stats
from .logging_utils import log_request
from .metrics import increment_http_request, increment_webhook_result, export_metrics
from fastapi.responses import Response


app = FastAPI(title="Lyftr AI Backend")


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware to log all requests with structured JSON output.
    Generates request_id, measures latency, and logs one line per request.
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Record start time
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Compute latency
    latency_ms = (time.time() - start_time) * 1000
    
    # Collect extra fields from request.state (if any)
    extra = {}
    if hasattr(request.state, "message_id"):
        extra["message_id"] = request.state.message_id
    if hasattr(request.state, "dup"):
        extra["dup"] = request.state.dup
    if hasattr(request.state, "result"):
        extra["result"] = request.state.result
    
    # Log the request
    log_request(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency_ms,
        extra=extra if extra else None
    )
    
    # Increment metrics
    increment_http_request(request.url.path, response.status_code)
    
    return response


# Pydantic model for webhook payload validation
class WebhookPayload(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from")
    to: str = Field(..., min_length=1)
    ts: str = Field(..., min_length=1)
    text: Optional[str] = Field(None, max_length=4096)
    
    @field_validator("from_")
    @classmethod
    def validate_from(cls, v: str) -> str:
        if not v.startswith("+"):
            raise ValueError("must start with +")
        if not v[1:].isdigit():
            raise ValueError("must contain only digits after +")
        return v
    
    @field_validator("to")
    @classmethod
    def validate_to(cls, v: str) -> str:
        if not v.startswith("+"):
            raise ValueError("must start with +")
        if not v[1:].isdigit():
            raise ValueError("must contain only digits after +")
        return v
    
    @field_validator("ts")
    @classmethod
    def validate_ts(cls, v: str) -> str:
        if not v.endswith("Z"):
            raise ValueError("must be ISO-8601 UTC ending with Z")
        return v


def verify_signature(body: bytes, signature: str) -> bool:
    """
    Verify HMAC-SHA256 signature using constant-time comparison.
    
    Args:
        body: Raw request body bytes
        signature: Hex-encoded signature from X-Signature header
    
    Returns:
        True if signature is valid, False otherwise
    """
    secret = config.WEBHOOK_SECRET.encode('utf-8')
    expected_signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        init_db()
    except Exception:
        # Don't crash on startup, let readiness check handle it
        pass


@app.get("/health/live")
async def health_live():
    """
    Liveness check - always returns 200.
    Indicates the application process is running.
    """
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready():
    """
    Readiness check - returns 200 only if:
    - Database is reachable and schema exists (check_db)
    - WEBHOOK_SECRET is present and non-empty (config.is_webhook_secret_valid)
    """
    db_ready = check_db()
    webhook_secret_valid = config.is_webhook_secret_valid()
    
    if db_ready and webhook_secret_valid:
        return {"status": "ready"}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"}
        )


@app.post("/webhook")
async def webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature")
):
    """
    Webhook endpoint with HMAC signature verification and idempotent message storage.
    
    Returns:
        200 {"status": "ok"} for valid requests (both new and duplicate messages)
        401 {"detail": "invalid signature"} for missing or invalid signatures
        422 for invalid payload (handled by FastAPI/Pydantic)
    """
    # Read raw body for HMAC verification
    raw_body = await request.body()
    
    # Verify signature
    if not x_signature:
        request.state.result = "invalid_signature"
        increment_webhook_result("invalid_signature")
        return JSONResponse(
            status_code=401,
            content={"detail": "invalid signature"}
        )
    
    if not verify_signature(raw_body, x_signature):
        request.state.result = "invalid_signature"
        increment_webhook_result("invalid_signature")
        return JSONResponse(
            status_code=401,
            content={"detail": "invalid signature"}
        )
    
    # Parse and validate payload
    try:
        payload = WebhookPayload.model_validate_json(raw_body)
    except ValidationError:
        request.state.result = "validation_error"
        increment_webhook_result("validation_error")
        raise
    
    # Set message_id on request.state
    request.state.message_id = payload.message_id
    
    # Get current timestamp for created_at
    created_at = datetime.utcnow().isoformat() + "Z"
    
    # Insert message (idempotent)
    result = insert_message(
        message_id=payload.message_id,
        from_msisdn=payload.from_,
        to_msisdn=payload.to,
        ts=payload.ts,
        text=payload.text,
        created_at=created_at
    )
    
    # Set logging fields on request.state
    request.state.dup = (result == "duplicate")
    request.state.result = result
    
    # Increment metrics
    increment_webhook_result(result)
    
    # Return success for both "created" and "duplicate"
    return {"status": "ok"}


@app.get("/messages")
async def get_messages(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    from_: Optional[str] = Query(default=None, alias="from"),
    since: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None)
):
    """
    Retrieve messages with optional filtering and pagination.
    
    Query parameters:
        limit: Maximum number of messages to return (1-100, default 50)
        offset: Number of messages to skip (default 0)
        from: Filter by sender phone number (optional)
        since: Filter by timestamp - messages with ts >= since (optional, ISO-8601)
        q: Search query for text field (optional)
    
    Returns:
        JSON with data (list of messages), total count, limit, and offset
    """
    # Fetch messages from storage
    messages, total = fetch_messages(
        limit=limit,
        offset=offset,
        from_msisdn=from_,
        since_ts=since,
        q=q
    )
    
    # Transform messages to exclude created_at field
    data = [
        {
            "message_id": msg["message_id"],
            "from": msg["from_msisdn"],
            "to": msg["to_msisdn"],
            "ts": msg["ts"],
            "text": msg["text"]
        }
        for msg in messages
    ]
    
    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/stats")
async def get_statistics():
    """
    Retrieve aggregate message-level statistics.
    """
    stats = get_stats()
    return stats


@app.get("/metrics")
async def get_metrics():
    """
    Expose Prometheus-style metrics.
    """
    content = export_metrics()
    return Response(content=content, media_type="text/plain")

