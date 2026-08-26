import os
import sqlite3
import datetime
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_history.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_memory_db():
    """
    Initializes the SQLite chat_history table if it does not exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_message(chat_id: str, role: str, content: str):
    """
    Saves a single chat message (user or assistant) to SQLite.
    """
    init_memory_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (chat_id, role, content) VALUES (?, ?, ?)",
        (str(chat_id), role, content)
    )
    conn.commit()
    conn.close()

def get_recent_history(chat_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Retrieves the most recent messages for a given chat_id.
    """
    init_memory_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
        (str(chat_id), limit)
    )
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in reversed(rows):
        history.append({"role": r["role"], "content": r["content"]})
    return history

def clear_history(chat_id: str):
    """
    Clears conversation memory for a chat_id.
    """
    init_memory_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE chat_id = ?", (str(chat_id),))
    conn.commit()
    conn.close()
