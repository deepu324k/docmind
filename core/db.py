"""
Database — SQLite session management and chat history storage.
"""

import os
import json
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "documind.db")


def _get_conn():
    """Get a SQLite connection with WAL mode for better concurrency."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize the database tables."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            doc_names TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            table_data TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
    """)
    conn.commit()
    conn.close()


def create_session(session_id, doc_names, table_data=None):
    """Create a new session record."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO sessions (id, doc_names, table_data) VALUES (?, ?, ?)",
        (session_id, json.dumps(doc_names), json.dumps(table_data) if table_data else None)
    )
    conn.commit()
    conn.close()


def update_session_docs(session_id, doc_names, table_data=None):
    """Update document names for an existing session."""
    conn = _get_conn()
    conn.execute(
        "UPDATE sessions SET doc_names = ?, table_data = ? WHERE id = ?",
        (json.dumps(doc_names), json.dumps(table_data) if table_data else None, session_id)
    )
    conn.commit()
    conn.close()


def get_session(session_id):
    """Get session info."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "doc_names": json.loads(row["doc_names"]),
            "created_at": row["created_at"],
            "table_data": json.loads(row["table_data"]) if row["table_data"] else None
        }
    return None


def save_chat(session_id, question, answer, sources):
    """Save a chat message to history."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO chat_history (session_id, question, answer, sources) VALUES (?, ?, ?, ?)",
        (session_id, question, answer, json.dumps(sources))
    )
    conn.commit()
    conn.close()


def get_history(session_id):
    """Get full chat history for a session."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,)
    ).fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "question": row["question"],
            "answer": row["answer"],
            "sources": json.loads(row["sources"]) if row["sources"] else [],
            "created_at": row["created_at"]
        })
    return history


def get_all_sessions():
    """Get all sessions (for session list)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    sessions = []
    for row in rows:
        sessions.append({
            "id": row["id"],
            "doc_names": json.loads(row["doc_names"]),
            "created_at": row["created_at"]
        })
    return sessions
