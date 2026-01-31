import json
from datetime import datetime
from typing import Optional
import logging

def log_request(
    request_id: str,
    method: str,
    path: str,
    status: int,
    latency_ms: float,
    extra: Optional[dict] = None
):
    """
    Log a JSON-formatted request log line to stdout.
    
    Args:
        request_id: Unique request identifier
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status: HTTP status code
        latency_ms: Request latency in milliseconds
        extra: Optional dictionary of additional fields
    """
    log_entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "request_id": request_id,
        "method": method,
        "path": path,
        "status": status,
        "latency_ms": latency_ms
    }
    
    # Merge extra fields if provided
    if extra:
        log_entry.update(extra)

    
    logger = logging.getLogger(__name__)
    logger.error("error message")
    
    # Output as a single JSON line
    print(json.dumps(log_entry), flush=True)
