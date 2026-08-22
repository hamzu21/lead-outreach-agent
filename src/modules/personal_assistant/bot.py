import time
import os
import json
import base64
from src.config import TELEGRAM_BOT_TOKEN
from src.services.telegram_service import (
    send_telegram_message,
    get_telegram_updates,
    get_telegram_file_bytes
)
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

def run_telegram_bot_loop():
    """
    Runs an interactive Telegram bot long-polling loop to handle commands and messages.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram Bot] Error: TELEGRAM_BOT_TOKEN is not set in environment or config!")
        return

    print("🤖 Starting Personal Assistant Telegram Bot...")
    print("Send /start, /brief, /expense, or /inbox to your bot in Telegram.")
    
    offset = 0
    service = PersonalAssistantService()

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

                print(f"[Telegram Bot] Message received from Chat ID {chat_id}: text='{text}', photos={bool(photos)}")

                # 1. Handle Photo (Receipt)
                if photos:
                    # Best quality photo is the last item in the list
                    best_photo = photos[-1]
                    handle_telegram_photo(chat_id, best_photo["file_id"], caption=caption)
                    continue

                # 2. Handle Text Commands
                if text.startswith("/start") or text.startswith("/help"):
                    welcome_msg = (
                        "👋 *Welcome to your AI Executive Assistant Bot!*\n\n"
                        "Here are the available commands:\n"
                        "• /brief or /morning - Generate Morning Executive Briefing\n"
                        "• /expense <text> - Log an expense (e.g. `/expense Paid 1500 PKR for lunch`)\n"
                        "• /inbox - Get categorized Inbox Digest & Action Items\n"
                        "• 📷 *Photo Receipt* - Upload a receipt photo anytime to auto-log expenses!"
                    )
                    send_telegram_message(welcome_msg, chat_id=chat_id)

                elif text.startswith("/brief") or text.startswith("/morning"):
                    send_telegram_message("🌅 *Generating your Morning Executive Briefing...*", chat_id=chat_id)
                    briefing = service.get_morning_briefing()
                    send_telegram_message(briefing, chat_id=chat_id)

                elif text.startswith("/inbox"):
                    send_telegram_message("📥 *Scanning inbox and generating digest...*", chat_id=chat_id)
                    digest = service.get_inbox_digest()
                    send_telegram_message(digest, chat_id=chat_id)

                elif text.startswith("/expense"):
                    expense_text = text.replace("/expense", "", 1).strip()
                    if not expense_text:
                        send_telegram_message("⚠️ Please provide expense details after `/expense`, e.g., `/expense Paid $45 for fuel`", chat_id=chat_id)
                    else:
                        send_telegram_message("🧾 *Processing expense entry...*", chat_id=chat_id)
                        run_expense_tracker_agent(expense_text, send_telegram=True)

                elif text:
                    # Arbitrary text input - check if it looks like an expense or general inquiry
                    if any(kw in text.lower() for kw in ["paid", "bought", "spent", "cost", "rs", "pkr", "$", "dollar", "receipt", "bill"]):
                        send_telegram_message("🧾 *Processing expense entry...*", chat_id=chat_id)
                        run_expense_tracker_agent(text, send_telegram=True)
                    else:
                        reply = generate_ai_content(f"You are a helpful executive personal assistant responding to the user's message on Telegram:\n\"{text}\"")
                        send_telegram_message(reply, chat_id=chat_id)

        except KeyboardInterrupt:
            print("\n[Telegram Bot] Stopped by user.")
            break
        except Exception as e:
            print(f"[Telegram Bot] Loop exception: {e}")
            time.sleep(3)
