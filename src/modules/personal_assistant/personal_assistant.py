import os
import json
import time
import datetime
from src.config import (
    EXPENSE_SPREADSHEET_ID,
    EXPENSE_SHEET_NAME,
    EXPENSE_EXCEL_PATH,
    LOCAL_EXCEL_PATH
)
from src.services.google_auth import get_google_services
from src.services.ai_generator import generate_ai_content
from src.services.telegram_service import send_telegram_message
from openpyxl import Workbook, load_workbook

class PersonalAssistantService:
    def __init__(self):
        self.sheets_service = None
        self.gmail_service = None

    def initialize_services(self):
        try:
            self.sheets_service, self.gmail_service = get_google_services()
        except Exception as e:
            print(f"[PersonalAssistant] Warning initializing Google services: {e}")

    def fetch_recent_emails(self, max_results: int = 15, query: str = "label:INBOX"):
        """
        Fetches metadata of recent emails from Gmail.
        """
        if not self.gmail_service:
            self.initialize_services()

        if not self.gmail_service:
            return []

        try:
            res = self.gmail_service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results
            ).execute()
            messages = res.get("messages", [])

            email_data = []
            for msg_meta in messages:
                msg = self.gmail_service.users().messages().get(
                    userId="me",
                    id=msg_meta["id"],
                    format="full"
                ).execute()

                payload = msg.get("payload", {})
                headers = payload.get("headers", [])

                subject = ""
                sender = ""
                date_str = ""

                for h in headers:
                    h_name = h.get("name", "").lower()
                    if h_name == "subject":
                        subject = h.get("value", "")
                    elif h_name == "from":
                        sender = h.get("value", "")
                    elif h_name == "date":
                        date_str = h.get("value", "")

                snippet = msg.get("snippet", "")
                email_data.append({
                    "id": msg_meta["id"],
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "snippet": snippet
                })
            return email_data
        except Exception as e:
            print(f"[PersonalAssistant] Error fetching emails: {e}")
            return []

    def get_morning_briefing(self) -> str:
        """
        Generates a comprehensive Morning Executive Briefing.
        """
        print("[PersonalAssistant] Generating Morning Briefing...")
        emails = self.fetch_recent_emails(max_results=10, query="is:unread label:INBOX")

        now_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
        
        prompt = f"""
You are an executive AI personal assistant. Create a clear, high-priority Morning Executive Briefing for today ({now_str}).

Context Data:
Unread Inbox Emails: {json.dumps(emails, indent=2)}

Requirements:
1. Provide a warm, professional morning greeting.
2. Highlight High Priority items / actionable emails (if any).
3. Provide a short summary of General Updates.
4. Give a motivating Tech/Coding Quote or Quick Insight for the day.
5. Format the output neatly using Telegram Markdown (use *bold*, bullet points, short paragraphs).

Keep it concise and easy to read on a mobile phone.
"""
        briefing_text = generate_ai_content(prompt)
        return briefing_text

    def process_expense(self, input_text: str) -> dict:
        """
        Extracts structured expense details from text/receipt using Gemini AI,
        and logs it to Google Sheet & Local Excel.
        """
        print(f"[PersonalAssistant] Processing expense input: {input_text[:50]}...")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d")

        prompt = f"""
Extract structured financial transaction data from the following text or receipt details:
"{input_text}"

Current Date: {now_str}

Extract and return JSON with keys:
- "date": "YYYY-MM-DD" (use current date if unspecified)
- "vendor": "Name of store/vendor/payee"
- "amount": numeric float value
- "currency": "PKR", "USD", etc.
- "category": Choose one of ["Food & Dining", "Tech & Subscriptions", "Utilities & Bills", "Travel & Transport", "Education & Books", "Personal & Misc"]
- "description": Short 1-sentence description

Return strict JSON:
{{
  "date": "2026-08-22",
  "vendor": "Vendor Name",
  "amount": 50.0,
  "currency": "USD",
  "category": "Category",
  "description": "Short description"
}}
"""
        raw_json = generate_ai_content(prompt, response_mime_type="application/json")
        data = json.loads(raw_json)

        # Log to Google Sheet & Local Excel
        self._log_expense_data(data)
        return data

    def _log_expense_data(self, data: dict):
        """
        Logs extracted expense row to Google Sheet and local expense_log.xlsx
        """
        date_val = data.get("date", "")
        vendor_val = data.get("vendor", "Unknown")
        amount_val = data.get("amount", 0.0)
        currency_val = data.get("currency", "USD")
        category_val = data.get("category", "Personal")
        desc_val = data.get("description", "")

        row = [date_val, vendor_val, amount_val, currency_val, category_val, desc_val]

        # 1. Update Google Sheet
        if not self.sheets_service:
            self.initialize_services()

        if self.sheets_service:
            try:
                # Ensure sheet tab exists
                body = {"values": [row]}
                self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=EXPENSE_SPREADSHEET_ID,
                    range=f"{EXPENSE_SHEET_NAME}!A:F",
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body=body
                ).execute()
                print("-> Appended expense to Google Sheet.")
            except Exception as e:
                print(f"Warning: Failed to update expense in Google Sheet: {e}")

        # 2. Update Local Excel
        try:
            excel_path = EXPENSE_EXCEL_PATH
            if not os.path.exists(excel_path):
                wb = Workbook()
                ws = wb.active
                ws.title = "Expenses"
                ws.append(["Date", "Vendor", "Amount", "Currency", "Category", "Description"])
            else:
                wb = load_workbook(excel_path)
                ws = wb.active

            ws.append(row)
            wb.save(excel_path)
            print(f"-> Appended expense to local Excel ({excel_path}).")
        except Exception as e:
            print(f"Warning: Failed to update local expense Excel: {e}")

    def get_inbox_digest(self) -> str:
        """
        Categorizes inbox emails and builds a structured summary.
        """
        print("[PersonalAssistant] Generating Inbox Digest...")
        emails = self.fetch_recent_emails(max_results=15, query="label:INBOX")

        if not emails:
            return "📥 *Inbox Digest*: No recent inbox messages found."

        prompt = f"""
Categorize and summarize the following unread/recent inbox emails:
{json.dumps(emails, indent=2)}

Group emails into the following categories:
- 🚨 *Action Required* (Emails needing direct reply or urgent action)
- 💳 *Bills & Financial* (Invoices, receipts, subscription notices)
- 👤 *Personal / Important* (Direct contacts)
- 📰 *Newsletters / Info* (General updates, non-urgent)

Format the response neatly for Telegram (Markdown). Keep summaries punchy and clear.
"""
        digest_text = generate_ai_content(prompt)
        return digest_text


def run_morning_brief_agent(send_telegram: bool = True):
    service = PersonalAssistantService()
    brief = service.get_morning_briefing()
    print("\n--- MORNING EXECUTIVE BRIEFING ---")
    print(brief)
    if send_telegram:
        success = send_telegram_message(brief)
        if success:
            print("[PersonalAssistant] Morning Briefing sent to Telegram successfully.")

def run_expense_tracker_agent(input_text: str, send_telegram: bool = True) -> dict:
    service = PersonalAssistantService()
    data = service.process_expense(input_text)
    msg = (
        f"✅ *Expense Logged Successfully*\n\n"
        f"• *Vendor*: {data.get('vendor')}\n"
        f"• *Amount*: {data.get('currency')} {data.get('amount')}\n"
        f"• *Category*: {data.get('category')}\n"
        f"• *Date*: {data.get('date')}\n"
        f"• *Note*: {data.get('description')}"
    )
    print("\n--- EXPENSE PROCESSED ---")
    print(msg)
    if send_telegram:
        send_telegram_message(msg)
    return data

def run_inbox_zero_agent(send_telegram: bool = True):
    service = PersonalAssistantService()
    digest = service.get_inbox_digest()
    print("\n--- INBOX DIGEST ---")
    print(digest)
    if send_telegram:
        send_telegram_message(digest)
