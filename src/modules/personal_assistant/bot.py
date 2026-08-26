import time
import os
import json
import base64
from src.config import TELEGRAM_BOT_TOKEN
from src.services.telegram_service import (
    send_telegram_message,
    get_telegram_updates,
    get_telegram_file_bytes,
    download_telegram_file
)
from src.services.slides_service import extract_text_from_file
from src.modules.personal_assistant.personal_assistant import (
    PersonalAssistantService,
    run_morning_brief_agent,
    run_expense_tracker_agent,
    run_inbox_zero_agent
)
from src.services.ai_generator import get_ai_client, generate_ai_content
from google.genai import types

def handle_telegram_photo(chat_id: str, file_id: str, caption: str = ""):
    """
    Handles receipt photo uploaded by user in Telegram.
    Uses Gemini Vision to read receipt and log expense.
    """
    send_telegram_message("📷 *Analyzing receipt photo with Gemini AI...*", chat_id=chat_id)
    image_bytes = get_telegram_file_bytes(file_id)

    if not image_bytes:
        send_telegram_message("❌ Failed to download photo from Telegram servers.", chat_id=chat_id)
        return

    try:
        client = get_ai_client()
        prompt = f"""
Analyze this receipt image and extract structured expense details.
Caption provided: "{caption}"

Return JSON with keys:
- "date": "YYYY-MM-DD"
- "vendor": "Store / Merchant Name"
- "amount": numeric float
- "currency": "PKR", "USD", etc.
- "category": "Food & Dining", "Tech & Subscriptions", "Utilities & Bills", "Travel & Transport", or "Personal & Misc"
- "description": "Summary of purchased items"
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ],
            config={"response_mime_type": "application/json"}
        )

        expense_data = json.loads(response.text.strip())
        service = PersonalAssistantService()
        service._log_expense_data(expense_data)

        msg = (
            f"🧾 *Receipt Logged Successfully*\n\n"
            f"• *Vendor*: {expense_data.get('vendor')}\n"
            f"• *Amount*: {expense_data.get('currency')} {expense_data.get('amount')}\n"
            f"• *Category*: {expense_data.get('category')}\n"
            f"• *Date*: {expense_data.get('date')}\n"
            f"• *Details*: {expense_data.get('description')}"
        )
        send_telegram_message(msg, chat_id=chat_id)
    except Exception as e:
        print(f"[Telegram Bot] Error analyzing photo receipt: {e}")
        send_telegram_message(f"⚠️ Could not parse receipt image: {e}", chat_id=chat_id)

import http.server
import socketserver
import threading

def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Zeyra AI Bot is running online 24/7!")
        def log_message(self, format, *args):
            pass  # Silent health check logs

    def run_server():
        try:
            with socketserver.TCPServer(("", port), HealthHandler) as httpd:
                print(f"[Health Check] Server listening on port {port}")
                httpd.serve_forever()
        except Exception as e:
            print(f"[Health Check] Notice: {e}")

    t = threading.Thread(target=run_server, daemon=True)
    t.start()

from src.services.reminder_service import get_due_reminders, mark_reminder_sent

def start_reminder_scheduler_thread():
    """
    Background daemon thread that checks SQLite for due scheduled reminders every 15 seconds,
    and dispatches Telegram alerts when due.
    """
    def reminder_loop():
        print("[Reminder Scheduler] Background scheduler initialized and active (polling every 15s)...")
        while True:
            try:
                due = get_due_reminders()
                for r in due:
                    r_id = r["id"]
                    r_chat_id = r["chat_id"]
                    r_text = r["reminder_text"]
                    r_time = r["remind_at"]
                    
                    alert_msg = (
                        f"⏰ *SCHEDULED REMINDER ALERT!* ⏰\n\n"
                        f"📌 *Task / Reminder*: {r_text}\n"
                        f"🕒 *Scheduled Time*: `{r_time}`\n\n"
                        f"_(Reminder ID #{r_id} triggered automatically)_"
                    )
                    success = send_telegram_message(alert_msg, chat_id=r_chat_id)
                    if success:
                        mark_reminder_sent(r_id)
            except Exception as e:
                print(f"[Reminder Scheduler] Notice: {e}")
            time.sleep(15)

    t = threading.Thread(target=reminder_loop, daemon=True)
    t.start()

from src.modules.personal_assistant.agent_engine import ConversationalAgent
from src.services.memory_db import clear_history

def run_telegram_bot_loop():
    """
    Runs an interactive Telegram bot long-polling loop with full conversational AI memory & function calling.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram Bot] Error: TELEGRAM_BOT_TOKEN is not set in environment or config!")
        return

    start_health_server()
    start_reminder_scheduler_thread()
    print("🤖 Starting Zeyra Conversational AI Agent on Telegram...")
    print("Send any conversational message or commands to your bot in Telegram.")
    
    offset = 0
    agent = ConversationalAgent()

    while True:
        try:
            updates = get_telegram_updates(offset=offset, timeout=10)
            for update in updates:
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat_id = str(message["chat"]["id"])
                text = message.get("text", "").strip()
                photos = message.get("photo")
                caption = message.get("caption", "")
                document = message.get("document")

                print(f"[Zeyra Agent] Message received from Chat ID {chat_id}: text='{text}', photos={bool(photos)}, doc={bool(document)}")

                # 1. Handle Photo (Receipt parsing)
                if photos:
                    best_photo = photos[-1]
                    handle_telegram_photo(chat_id, best_photo["file_id"], caption=caption)
                    continue

                # 2. Handle Document (PDF, Word, TXT uploads for Slides & Docs)
                if document:
                    file_id = document.get("file_id")
                    file_name = document.get("file_name", "document.pdf")
                    print(f"[Zeyra Agent] Document received from Chat ID {chat_id}: '{file_name}' (ID: {file_id})")
                    
                    local_path = download_telegram_file(file_id, file_name)
                    
                    if local_path:
                        if caption:
                            # User provided specific guidelines in caption (e.g. "Chapter 1 ki slides banao")
                            send_telegram_message(f"📥 *Received document*: `{file_name}` with guidelines: _{caption}_\n\nGenerating High-Contrast White Presentation Slides...", chat_id=chat_id)
                            doc_text = extract_text_from_file(local_path)
                            full_user_input = f"User Guidelines for Document: {caption}\n\nDocument File: {file_name}\nExtracted Content:\n{doc_text[:6000]}"
                            reply = agent.process_message(chat_id=chat_id, user_text=full_user_input)
                            send_telegram_message(reply, chat_id=chat_id)
                        else:
                            # No caption provided -> Analyze topics and ask user for guidelines
                            from src.services.slides_service import analyze_document_topics
                            analysis = analyze_document_topics(local_path)
                            doc_title = analysis.get("document_title", file_name)
                            topics = analysis.get("chapters_or_topics", [])
                            
                            topic_list_str = "\n".join([f"• *{t}*" for t in topics]) if topics else "• *General Overview & Chapters*"
                            
                            guidelines_msg = (
                                f"📥 *Document Received*: `{file_name}`\n\n"
                                f"Main ne aap ke document (_{doc_title}_) me yeh chapters/topics analyze kiye hain:\n"
                                f"{topic_list_str}\n\n"
                                f"👉 *Guidelines Needed*: Aap kis specific chapter ya topic ki slides banana chahte hain?\n"
                                f"_(Maslan bolein: 'Chapter 1 ki slides banao', 'Topic 2 ki presentation banao', ya 'Poori book ki slides banao')_"
                            )
                            send_telegram_message(guidelines_msg, chat_id=chat_id)
                    else:
                        send_telegram_message("⚠️ Could not download uploaded document from Telegram.", chat_id=chat_id)
                    continue

                # 2. Handle System Commands
                if text.startswith("/start") or text.startswith("/help"):
                    welcome_msg = (
                        "✨ *Hi Hamza! I am Zeyra, your AI Executive Assistant.*\n\n"
                        "I am fully conversational! You can talk to me naturally, ask me to log expenses, "
                        "check your emails, give you a morning briefing, or discuss anything.\n\n"
                        "💡 *Express Shortcuts*:\n"
                        "• `/brief` - Morning Executive Briefing\n"
                        "• `/inbox` - Inbox Digest & Action Items\n"
                        "• `/clear` - Clear conversation memory\n"
                        "• 📷 *Send Photo* - Upload a receipt to auto-log expenses!"
                    )
                    send_telegram_message(welcome_msg, chat_id=chat_id)
                    continue

                elif text.startswith("/clear"):
                    clear_history(chat_id)
                    send_telegram_message("🧹 *Conversation memory cleared.* How can I help you now?", chat_id=chat_id)
                    continue

                # 3. Full Conversational Engine (Memory + Agentic Tool Execution)
                if text:
                    reply = agent.process_message(chat_id=chat_id, user_text=text)
                    send_telegram_message(reply, chat_id=chat_id)

        except KeyboardInterrupt:
            print("\n[Zeyra Agent] Stopped by user.")
            break
        except Exception as e:
            print(f"[Zeyra Agent] Loop exception: {e}")
            time.sleep(3)
