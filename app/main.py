from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .models import init_db, check_db
from .config import config


app = FastAPI(title="Lyftr AI Backend")


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
    """Liveness check - always returns 200."""
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready():
    """
    Readiness check - returns 200 only if:
    - Database is reachable and schema exists
    - WEBHOOK_SECRET is present and non-empty
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
