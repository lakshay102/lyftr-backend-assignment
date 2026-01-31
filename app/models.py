import sqlite3
import os
from pathlib import Path
from .config import config


_db_connection = None


def _get_db_path() -> str:
    """Parse DATABASE_URL and return the file path."""
    db_url = config.DATABASE_URL
    
    # Expected format: sqlite:////data/app.db
    if not db_url.startswith("sqlite:///"):
        raise ValueError(f"Invalid DATABASE_URL format: {db_url}")
    
    # Remove the sqlite:/// prefix
    db_path = db_url[len("sqlite:///"):]
    
    return db_path


def _ensure_db_directory(db_path: str):
    """Ensure the directory for the database file exists."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        Path(db_dir).mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """
    Get or create a database connection.
    Connection is configured with Row factory for dict-like access.
    """
    global _db_connection
    
    if _db_connection is None:
        db_path = _get_db_path()
        _ensure_db_directory(db_path)
        _db_connection = sqlite3.connect(db_path, check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row
    
    return _db_connection


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT NOT NULL,
            from_msisdn TEXT NOT NULL,
            to_msisdn TEXT NOT NULL,
            ts TEXT NOT NULL,
            text TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()


def check_db() -> bool:
    """
    Check if the database is reachable and schema exists.
    Returns True if successful, False otherwise.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if messages table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='messages'
        """)
        
        result = cursor.fetchone()
        return result is not None
    except Exception:
        return False
