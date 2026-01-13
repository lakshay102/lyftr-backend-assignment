from typing import Optional, Literal
import sqlite3
from .models import get_connection


def insert_message(
    message_id: str,
    from_msisdn: str,
    to_msisdn: str,
    ts: str,
    text: Optional[str],
    created_at: str
) -> Literal["created", "duplicate"]:
    """
    Insert a message into the database.
    
    Returns:
        "created" if the message was inserted successfully
        "duplicate" if a message with the same message_id already exists
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (message_id, from_msisdn, to_msisdn, ts, text, created_at)
        )
        conn.commit()
        return "created"
    except sqlite3.IntegrityError:
        # Primary key constraint violation - duplicate message_id
        return "duplicate"


def fetch_messages(
    limit: int,
    offset: int,
    from_msisdn: Optional[str],
    since_ts: Optional[str],
    q: Optional[str]
) -> tuple[list[dict], int]:
    """
    Fetch messages with optional filters and pagination.
    
    Args:
        limit: Maximum number of rows to return
        offset: Number of rows to skip
        from_msisdn: Filter by sender phone number (optional)
        since_ts: Filter by timestamp - messages with ts >= since_ts (optional)
        q: Search query for text field (case-insensitive substring match, optional)
    
    Returns:
        Tuple of (list of message dicts, total count)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build WHERE clause
    where_conditions = []
    params = []
    
    if from_msisdn is not None:
        where_conditions.append("from_msisdn = ?")
        params.append(from_msisdn)
    
    if since_ts is not None:
        where_conditions.append("ts >= ?")
        params.append(since_ts)
    
    if q is not None:
        where_conditions.append("text LIKE ?")
        params.append(f"%{q}%")
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Query 1: Get total count
    count_query = f"SELECT COUNT(*) as total FROM messages {where_clause}"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()["total"]
    
    # Query 2: Get actual rows with limit/offset
    data_query = f"""
        SELECT message_id, from_msisdn, to_msisdn, ts, text, created_at
        FROM messages
        {where_clause}
        ORDER BY ts ASC, message_id ASC
        LIMIT ? OFFSET ?
    """
    cursor.execute(data_query, params + [limit, offset])
    
    rows = cursor.fetchall()
    
    # Convert Row objects to dicts
    messages = [dict(row) for row in rows]
    
    return messages, total_count
