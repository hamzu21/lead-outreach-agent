import os
import glob
import re
import time
from src.services.google_auth import get_google_services
from src.services.gmail_service import send_gmail_message
from src.services.ai_generator import generate_ai_content
from src.services.course_knowledge_service import query_course_context, index_course_material

STUDENT_DOMAINS = ["kfueit.edu.pk", "edu.pk", "student"]
STUDENT_KEYWORDS = [
    "student", "assignment", "lecture", "slides", "deadline", "quiz",
    "midterm", "final", "course", "class", "project", "lab", "syllabus",
    "kfueit", "sir", "professor", "instructor", "attendance", "grace marks"
]

def is_student_email(sender_email: str, subject: str = "", body: str = "") -> bool:
    """
    Detects if an incoming email is from a KFUEIT student or contains student academic query.
    """
    sender_lower = (sender_email or "").lower()
    content_lower = f"{subject} {body}".lower()

    # 1. Match student domain
    if any(domain in sender_lower for domain in STUDENT_DOMAINS):
        return True

    # 2. Match student academic keywords
    matches = [kw for kw in STUDENT_KEYWORDS if kw in content_lower]
    return len(matches) >= 2

def resolve_requested_course_file(query_text: str) -> str:
    """
    Finds requested course slides, lab manuals, assignment PDFs, or syllabus files from 
    Zeyra's DB indexed files, course_materials/ folder, or local storage.
    """
    from src.services.course_knowledge_service import find_indexed_file_for_query
    
    # 1. Search SQLite DB indexed physical files first
    db_file = find_indexed_file_for_query(query_text)
    if db_file and os.path.exists(db_file):
        print(f"[StudentAssistant] Resolved physical file from DB: {db_file}")
        return db_file

    query_lower = query_text.lower()
    
    # Check if student asked for file attachment
    if not any(kw in query_lower for kw in ["slide", "slides", "manual", "lab", "pdf", "docx", "pptx", "file", "attachment", "notes", "material", "syllabus", "presentation"]):
        return None

    # 2. Search local directory files (.pptx, .pdf, .docx, .zip)
    all_files = (
        glob.glob("course_materials/*") +
        glob.glob("*.pptx") + glob.glob("*.pdf") + glob.glob("*.docx") + glob.glob("*.zip") +
        glob.glob("assets/*") + glob.glob("downloads/*")
    )
    
    words = [w for w in re.split(r'[\s_\-\.]+', query_lower) if len(w) > 2]

    for f_path in all_files:
        if not os.path.isfile(f_path):
            continue
        basename_lower = os.path.basename(f_path).lower()
        for w in words:
            if w in basename_lower:
                print(f"[StudentAssistant] Matched physical file for '{w}': {f_path}")
                return os.path.abspath(f_path)

    return None

def generate_student_reply(sender_email: str, subject: str, query_body: str) -> dict:
    """
    Generates an intelligent AI response for a student query using stored course knowledge.
    """
    course_context = query_course_context(query_body)
    attachment_path = resolve_requested_course_file(query_body)

    prompt = f"""
You are an AI Academic Assistant responding to a student inquiry on behalf of Instructor Muhammad Hamza (Khwaja Fareed University of Engineering & IT - KFUEIT).

Student Email: {sender_email}
Email Subject: {subject}
Student Query / Message: "{query_body}"

Stored Course Knowledge / Syllabus Context:
{course_context}

Requirements:
1. Polite, encouraging, clear, and professional academic tone.
2. Direct answer to the student's question based on course guidelines.
3. If the student requested course slides, lecture notes, or files, inform them that the file is attached to this email.
4. Sign off politely as:
   "Best regards,
   Muhammad Hamza
   Faculty / Instructor, KFUEIT"

Return JSON:
{{
  "reply_subject": "Re: {subject or 'Course Inquiry'}",
  "reply_body": "Polite email body text"
}}
"""
    try:
        raw_json = generate_ai_content(prompt, response_mime_type="application/json")
        clean_str = raw_json.strip().strip("`").replace("json\n", "")
        import json
        data = json.loads(clean_str)
        return {
            "success": True,
            "subject": data.get("reply_subject", f"Re: {subject}"),
            "body": data.get("reply_body", "Thank you for reaching out. Please see attached course materials."),
            "attachment_path": attachment_path
        }
    except Exception as e:
        print(f"[StudentAssistant] Error generating student reply: {e}")
        fallback_body = f"Dear Student,\n\nThank you for reaching out regarding '{subject}'. I have received your message and will review your query shortly.\n\nBest regards,\nMuhammad Hamza\nInstructor, KFUEIT"
        return {
            "success": True,
            "subject": f"Re: {subject}",
            "body": fallback_body,
            "attachment_path": attachment_path
        }

SENSITIVE_KEYWORDS = [
    "grade", "marks", "re-check", "recheck", "re-eval", "reeval", "dispute", "fail",
    "medical", "sick", "hospital", "leave", "absence", "missed exam", "missed quiz",
    "cheating", "plagiarism", "extenuating", "emergency"
]

def is_sensitive_student_query(subject: str = "", body: str = "") -> dict:
    """
    Checks if a student query involves sensitive academic matters (grades, medical leave, missed exams)
    which require human review and approval.
    """
    content = f"{subject} {body}".lower()
    found = [kw for kw in SENSITIVE_KEYWORDS if kw in content]
    if found:
        return {
            "is_sensitive": True,
            "reason": f"Matched sensitive topic: {', '.join(found)}"
        }
    return {"is_sensitive": False, "reason": ""}

def process_incoming_student_queries(gmail_service=None, send_telegram_alerts: bool = True) -> dict:
    """
    Scans unread inbox emails, detects student inquiries, generates AI responses,
    attaches requested course slides/files, auto-replies for routine queries,
    and creates Gmail Drafts + Telegram Alerts for sensitive queries.
    """
    if not gmail_service:
        sheets, gmail_service, docs, drive = get_google_services()

    if not gmail_service:
        return {"success": False, "error": "Gmail API service unavailable"}

    print("[StudentAssistant] Scanning Gmail inbox for unread student inquiries...")
    try:
        res = gmail_service.users().messages().list(
            userId="me",
            q="label:INBOX is:unread",
            maxResults=15
        ).execute()
        messages = res.get("messages", [])

        if not messages:
            return {"success": True, "replied_count": 0, "drafted_count": 0, "message": "No unread student emails found in inbox."}

        replied_count = 0
        drafted_count = 0
        details = []

        for m_meta in messages:
            m_id = m_meta["id"]
            msg = gmail_service.users().messages().get(
                userId="me",
                id=m_id,
                format="full"
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            sender_email = ""
            subject_str = ""
            for h in headers:
                if h.get("name", "").lower() == "from":
                    sender_email = h.get("value", "")
                elif h.get("name", "").lower() == "subject":
                    subject_str = h.get("value", "")

            snippet = msg.get("snippet", "")

            if is_student_email(sender_email, subject=subject_str, body=snippet):
                print(f"[StudentAssistant] Detected Student Query from '{sender_email}' | Subject: '{subject_str}'")
                
                reply_data = generate_student_reply(
                    sender_email=sender_email,
                    subject=subject_str,
                    query_body=snippet
                )

                sens = is_sensitive_student_query(subject=subject_str, body=snippet)
                attach_file = reply_data.get("attachment_path")

                if sens["is_sensitive"]:
                    # SENSITIVE QUERY -> Save to Gmail Drafts & send Telegram Alert
                    from src.services.gmail_service import create_gmail_draft
                    draft_id = create_gmail_draft(
                        gmail_service=gmail_service,
                        to_email=sender_email,
                        subject=reply_data["subject"],
                        body_text=reply_data["body"],
                        attachment_path=attach_file
                    )
                    drafted_count += 1
                    print(f" -> Sensitive query from {sender_email}: Saved Draft ID #{draft_id}")

                    if send_telegram_alerts:
                        from src.services.telegram_service import send_telegram_message
                        alert_msg = (
                            f"🚨 *SENSITIVE STUDENT QUERY ALERT* 🚨\n\n"
                            f"• *Student*: `{sender_email}`\n"
                            f"• *Subject*: _{subject_str}_\n"
                            f"• *Reason*: `{sens['reason']}`\n"
                            f"• *Query*: \"{snippet[:160]}...\"\n\n"
                            f"💡 *Action Taken*: Prepared Gmail Draft (ID #{draft_id}). Please review in Gmail before dispatching."
                        )
                        send_telegram_message(alert_msg)

                    details.append({
                        "student_email": sender_email,
                        "subject": subject_str,
                        "status": "Saved to Drafts (Sensitive)",
                        "attached_file": os.path.basename(attach_file) if attach_file else "None"
                    })
                else:
                    # ROUTINE QUERY -> Auto-reply via Gmail API
                    res_send = send_gmail_message(
                        gmail_service=gmail_service,
                        to_email=sender_email,
                        subject=reply_data["subject"],
                        body_text=reply_data["body"],
                        attachment_path=attach_file
                    )
                    replied_count += 1
                    print(f" -> Sent automated reply to student {sender_email} (Msg ID: {res_send})")

                    details.append({
                        "student_email": sender_email,
                        "subject": subject_str,
                        "status": "Auto-Replied",
                        "attached_file": os.path.basename(attach_file) if attach_file else "None"
                    })

                # Mark original message as read
                try:
                    gmail_service.users().messages().batchModify(
                        userId="me",
                        body={"ids": [m_id], "removeLabelIds": ["UNREAD"]}
                    ).execute()
                except Exception:
                    pass

        return {
            "success": True,
            "replied_count": replied_count,
            "drafted_count": drafted_count,
            "details": details
        }

    except Exception as e:
        print(f"[StudentAssistant] Error processing student queries: {e}")
        return {"success": False, "error": str(e)}
