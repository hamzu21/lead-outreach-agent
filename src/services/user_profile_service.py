import os
import sqlite3
import json
from src.services.time_utils import get_pkt_now_str
from src.services.ai_generator import generate_ai_content

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_history.db")

def init_user_profiles_db():
    """
    Initializes the SQLite user_profiles table if it does not exist.
    """
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            chat_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            relationship TEXT DEFAULT 'Guest',
            notes TEXT DEFAULT '',
            language TEXT DEFAULT 'Urdu/English',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_or_create_user_profile(chat_id: str, name_fallback: str = "Friend") -> dict:
    """
    Retrieves or initializes a user profile by Telegram chat_id.
    """
    init_user_profiles_db()
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profiles WHERE chat_id = ?", (str(chat_id),))
    row = cursor.fetchone()

    if row:
        # Update last seen
        cursor.execute("UPDATE user_profiles SET last_seen = ? WHERE chat_id = ?", (get_pkt_now_str(), str(chat_id)))
        conn.commit()
        profile = dict(row)
        conn.close()
        return profile
    else:
        # Default profile for Hamza or new user
        is_hamza = (str(chat_id) == "6025459635" or "hamza" in name_fallback.lower())
        rel = "Hamza (Boss/Partner)" if is_hamza else "Guest/Friend"
        name = "Muhammad Hamza" if is_hamza else name_fallback

        cursor.execute("""
            INSERT INTO user_profiles (chat_id, name, relationship, notes, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(chat_id), name, rel, "", get_pkt_now_str(), get_pkt_now_str()))
        conn.commit()
        conn.close()
        return {
            "chat_id": str(chat_id),
            "name": name,
            "relationship": rel,
            "notes": "",
            "language": "Urdu/English"
        }

def update_user_profile(chat_id: str, name: str = None, relationship: str = None, new_note: str = None) -> dict:
    """
    Updates profile details or appends notes about a user.
    """
    profile = get_or_create_user_profile(chat_id)
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()

    updated_name = name or profile["name"]
    updated_rel = relationship or profile["relationship"]
    
    current_notes = profile.get("notes", "") or ""
    if new_note:
        if current_notes:
            current_notes += f" | {new_note}"
        else:
            current_notes = new_note

    cursor.execute("""
        UPDATE user_profiles
        SET name = ?, relationship = ?, notes = ?, last_seen = ?
        WHERE chat_id = ?
    """, (updated_name, updated_rel, current_notes, get_pkt_now_str(), str(chat_id)))
    conn.commit()
    conn.close()

    return {
        "chat_id": str(chat_id),
        "name": updated_name,
        "relationship": updated_rel,
        "notes": current_notes
    }

def register_guest_introduction(host_chat_id: str, intro_text: str) -> dict:
    """
    Extracts guest information when Hamza introduces someone to Zeyra in chat.
    e.g. 'Zeyra yeh mera dost Ali hai, is se milo. Yeh React developer hai'
    """
    prompt = f"""
Hamza is introducing a new guest/person to Zeyra. Extract person details:
"{intro_text}"

Return JSON:
{{
  "guest_name": "Full name or first name",
  "relationship": "Friend" | "Client" | "Colleague" | "Family" | "Guest",
  "key_facts": "Short notes about this person (profession, interest, topic)"
}}
"""
    try:
        raw_res = generate_ai_content(prompt, response_mime_type="application/json")
        clean_str = raw_res.strip().strip("`").replace("json\n", "")
        data = json.loads(clean_str)
        name = data.get("guest_name", "Guest")
        rel = data.get("relationship", "Friend")
        facts = data.get("key_facts", intro_text)
        return {"success": True, "name": name, "relationship": rel, "notes": facts}
    except Exception as e:
        print(f"[UserProfile] Parsing error: {e}")
        return {"success": False, "name": "Guest", "relationship": "Friend", "notes": intro_text}
