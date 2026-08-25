import os
import sqlite3
import datetime
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_history.db")

def init_reminders_db():
    """
    Initializes the SQLite reminders table if it does not exist.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            reminder_text TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_reminder(chat_id: str, reminder_text: str, remind_at_str: str) -> dict:
    """
    Saves a new reminder to SQLite.
    remind_at_str formatted as "YYYY-MM-DD HH:MM:SS"
    """
    init_reminders_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (chat_id, reminder_text, remind_at, status) VALUES (?, ?, ?, 'PENDING')",
        (str(chat_id), reminder_text, remind_at_str)
    )
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"[ReminderService] Saved reminder #{reminder_id} for chat {chat_id} at {remind_at_str}: '{reminder_text}'")
    return {
        "success": True,
        "id": reminder_id,
        "reminder_text": reminder_text,
        "remind_at": remind_at_str
    }

def get_due_reminders() -> List[Dict]:
    """
    Fetches all pending reminders where remind_at is past or equal to current time.
    """
    init_reminders_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "SELECT id, chat_id, reminder_text, remind_at FROM reminders WHERE status = 'PENDING' AND remind_at <= ?",
        (now_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "chat_id": r["chat_id"],
            "reminder_text": r["reminder_text"],
            "remind_at": r["remind_at"]
        })
    return res

def mark_reminder_sent(reminder_id: int):
    """
    Marks a reminder as SENT so it won't trigger again.
    """
    init_reminders_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET status = 'SENT' WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
    print(f"[ReminderService] Marked reminder #{reminder_id} as SENT.")

def get_pending_reminders(chat_id: str) -> List[Dict]:
    """
    Lists active pending reminders for a specific chat_id.
    """
    init_reminders_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, reminder_text, remind_at FROM reminders WHERE chat_id = ? AND status = 'PENDING' ORDER BY remind_at ASC",
        (str(chat_id),)
    )
    rows = cursor.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "reminder_text": r["reminder_text"],
            "remind_at": r["remind_at"]
        })
    return res
