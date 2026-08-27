import sqlite3
import os
import datetime
from src.services.slides_service import extract_text_from_file

DB_PATH = os.path.join(os.getcwd(), "chat_history.db")

def init_course_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT DEFAULT 'GENERAL',
            title TEXT NOT NULL,
            content_text TEXT NOT NULL,
            file_path TEXT DEFAULT '',
            drive_file_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_course_db()

def index_course_material(course_code: str, title: str, file_path_or_text: str, drive_file_id: str = "") -> dict:
    """
    Indexes a course syllabus, lecture note, slide, or text content into Zeyra's brain.
    """
    init_course_db()
    content_text = ""
    file_path = ""

    if os.path.exists(file_path_or_text):
        file_path = file_path_or_text
        content_text = extract_text_from_file(file_path)
        if not content_text:
            content_text = f"Course file: {os.path.basename(file_path)}"
    else:
        content_text = file_path_or_text

    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO course_knowledge (course_code, title, content_text, file_path, drive_file_id)
        VALUES (?, ?, ?, ?, ?)
    """, (course_code.upper().strip(), title.strip(), content_text, file_path, drive_file_id))
    
    mat_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"[CourseKnowledge] Indexed '{title}' under course '{course_code}' (ID #{mat_id})")
    return {
        "success": True,
        "id": mat_id,
        "course_code": course_code.upper().strip(),
        "title": title,
        "char_count": len(content_text)
    }

def get_all_course_materials(course_code: str = None) -> list:
    init_course_db()
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    if course_code:
        cursor.execute("SELECT id, course_code, title, file_path, drive_file_id, created_at FROM course_knowledge WHERE course_code = ? ORDER BY id DESC", (course_code.upper().strip(),))
    else:
        cursor.execute("SELECT id, course_code, title, file_path, drive_file_id, created_at FROM course_knowledge ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "course_code": r[1],
            "title": r[2],
            "file_path": r[3],
            "drive_file_id": r[4],
            "created_at": r[5]
        })
    return results

def query_course_context(query_text: str, course_code: str = None) -> str:
    """
    Retrieves relevant stored course knowledge for Gemini AI response generation.
    """
    init_course_db()
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    
    if course_code:
        cursor.execute("SELECT title, content_text FROM course_knowledge WHERE course_code = ? ORDER BY id DESC LIMIT 5", (course_code.upper().strip(),))
    else:
        cursor.execute("SELECT title, content_text FROM course_knowledge ORDER BY id DESC LIMIT 10")
    
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No specific course materials stored in brain yet."

    context_str = "--- STORED COURSE KNOWLEDGE & SYLLABUS ---\n"
    for r in rows:
        title, text = r[0], r[1]
        context_str += f"\nTitle: {title}\nContent:\n{text[:3000]}\n"
    
    return context_str
