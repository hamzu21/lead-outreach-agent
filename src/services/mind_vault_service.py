import os
import sqlite3
import json
from typing import List, Dict
from src.services.time_utils import get_pkt_now_str
from src.services.ai_generator import generate_ai_content

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_history.db")

def init_mind_vault_db():
    """
    Initializes the SQLite mind_vault table if it does not exist.
    """
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mind_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            category TEXT DEFAULT 'Personal',
            fact_key TEXT NOT NULL,
            fact_value TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_fact(chat_id: str, fact_text: str) -> dict:
    """
    Uses Gemini AI to categorize and structure the personal fact, then saves to SQLite.
    """
    init_mind_vault_db()
    
    prompt = f"""
Extract structured personal knowledge fact from this user input:
"{fact_text}"

Return JSON with format:
{{
  "category": "Vehicle" | "Tech/Credentials" | "Personal/Home" | "Finance" | "Health" | "General",
  "fact_key": "Short topic summary / title",
  "fact_value": "Complete clear detail to remember"
}}
"""
    try:
        raw_json = generate_ai_content(prompt, response_mime_type="application/json")
        clean_str = raw_json.strip().strip("`").replace("json\n", "")
        data = json.loads(clean_str)
        cat = data.get("category", "Personal")
        key = data.get("fact_key", fact_text[:30])
        val = data.get("fact_value", fact_text)
    except Exception as e:
        print(f"[MindVault] Parsing notice: {e}")
        cat = "Personal"
        key = "Fact Note"
        val = fact_text

    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mind_vault (chat_id, category, fact_key, fact_value, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(chat_id), cat, key, val, get_pkt_now_str())
    )
    fact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[MindVault] Saved fact #{fact_id}: [{cat}] {key} -> {val}")
    return {
        "success": True,
        "id": fact_id,
        "category": cat,
        "fact_key": key,
        "fact_value": val,
        "created_at": get_pkt_now_str()
    }

def query_vault(chat_id: str, query_text: str) -> str:
    """
    Retrieves facts from mind_vault and uses Gemini to answer the user's recall question.
    """
    init_mind_vault_db()
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, category, fact_key, fact_value, created_at FROM mind_vault WHERE chat_id = ? ORDER BY id DESC LIMIT 50",
        (str(chat_id),)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "🧠 *Zeyra Mind Vault*: No stored facts found in your personal knowledge vault yet."

    vault_facts = []
    for r in rows:
        vault_facts.append({
            "id": r["id"],
            "category": r["category"],
            "topic": r["fact_key"],
            "detail": r["fact_value"],
            "date": r["created_at"]
        })

    prompt = f"""
You are Zeyra, searching Hamza's Personal Mind Vault to answer his question accurately.

User's Question: "{query_text}"

Stored Mind Vault Facts:
{json.dumps(vault_facts, indent=2)}

Answer the user's question clearly, concisely, and warmly based ONLY on the stored facts. Cite the date if relevant.
If no relevant fact is found in the vault, politely state that you haven't recorded that specific fact yet.
"""
    answer = generate_ai_content(prompt)
    return answer
