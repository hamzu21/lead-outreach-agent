import time
from src.config import SPREADSHEET_ID, SHEET_NAME, LOCAL_EXCEL_PATH
from src.services.google_auth import get_google_services
from src.services.web_auditor import inspect_website
from src.services.ai_generator import analyze_and_draft_email
from src.services.gmail_service import create_gmail_draft
from src.services.whatsapp_service import generate_whatsapp_link
from src.services.storage import (
    ensure_google_sheet_header,
    update_google_sheet_status,
    update_local_excel
)

class LeadOutreachAgent:
    def __init__(self, limit: int = 10):
        self.limit = limit
        self.sheets_service = None
        self.gmail_service = None

    def initialize_services(self):
        print("Initializing Google API services...")
        self.sheets_service, self.gmail_service, _, _ = get_google_services()
        ensure_google_sheet_header(self.sheets_service)

    def run(self):
        if not self.sheets_service or not self.gmail_service:
            self.initialize_services()

        print(f"Fetching lead data from Google Sheet ({SPREADSHEET_ID})...")
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A2:J"
        ).execute()
        rows = result.get("values", [])

        processed_count = 0

        for idx, row in enumerate(rows, start=2):
            if processed_count >= self.limit:
                print(f"\nReached batch limit of {self.limit}. Stopping execution.")
                break

            business_name = row[0] if len(row) > 0 else ""
            location = row[1] if len(row) > 1 else ""
            industry = row[2] if len(row) > 2 else ""
            phone = row[3] if len(row) > 3 else ""
            email = row[4] if len(row) > 4 else ""
            social = row[5] if len(row) > 5 else ""
            status = row[6] if len(row) > 6 else ""
            outreach_status = row[8] if len(row) > 8 else (row[7] if len(row) > 7 and "Draft" in row[7] else "")

            # Skip invalid emails or leads already processed
            if not email or email == "N/A" or "@" not in email or "Draft Created" in outreach_status or "Draft Created" in status:
                continue

            print(f"\n[{idx}] Processing Lead: {business_name} | {email}")

            try:
                # 1. Perform Web Audit
                website_url = status if "http" in status else None
                audit = inspect_website(website_url)

                lead_info = {
                    "name": business_name,
                    "location": location,
                    "industry": industry,
                    "phone": phone,
                    "email": email,
                    "social_link": social,
                    "website_status": status
                }

                # 2. Generate Personalized Email via Gemini AI
                content = analyze_and_draft_email(lead_info, audit)

                # 3. Create Draft in Gmail
                draft_id = create_gmail_draft(self.gmail_service, email, content["subject"], content["body"])
                print(f"-> Draft created successfully in Gmail (ID: {draft_id})")

                # 4. Generate 1-Click Free WhatsApp Action Link
                whatsapp_link = generate_whatsapp_link(phone, business_name, location)
                if whatsapp_link != "N/A":
                    print(f"-> Generated 1-Click WhatsApp Action Link: {whatsapp_link[:60]}...")
                else:
                    print("-> No valid phone number for WhatsApp action link.")

                # 5. Update Google Sheet (Columns I & J) & Local Excel Log
                update_google_sheet_status(self.sheets_service, idx, draft_id, whatsapp_link)
                update_local_excel(business_name, email, location, industry, draft_id, content["subject"], whatsapp_link)
                print(f"-> Updated Google Sheet (Columns I & J) & Local Excel Log ({LOCAL_EXCEL_PATH})")

                processed_count += 1
                time.sleep(1)  # Rate limiting pause
            except Exception as e:
                print(f"-> Warning: Failed to process lead {business_name} ({email}): {e}. Continuing with next lead...")
                time.sleep(2)
                continue

        print(f"\nFinished processing batch. Total drafts created: {processed_count}")

def run_agent(limit: int = 10):
    agent = LeadOutreachAgent(limit=limit)
    agent.run()
