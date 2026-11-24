import os
import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

def get_db_path() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    return url

def get_connection():
    return sqlite3.connect(get_db_path())

def init_db():
    db_path = get_db_path()
    abs_dir = os.path.dirname(os.path.abspath(db_path))
    if abs_dir:
        os.makedirs(abs_dir, exist_ok=True)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        conn.commit()

def clear_db():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            conn.commit()
    except Exception:
        pass

def save_message(session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
    created_at = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(metadata) if metadata is not None else None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, meta_json, created_at)
        )
        conn.commit()

def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, metadata FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        result = []
        for role, content, meta_str in rows:
            msg: Dict[str, Any] = {"role": role, "content": content}
            if role == "assistant" and meta_str:
                try:
                    msg["metadata"] = json.loads(meta_str)
                except Exception:
                    msg["metadata"] = None
            result.append(msg)
        return result

def session_exists(session_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM messages WHERE session_id = ? LIMIT 1", (session_id,))
        return cursor.fetchone() is not None
