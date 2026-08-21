import os
import time
import datetime
from src.config import JOB_SPREADSHEET_ID, JOB_SHEET_NAME, LOCAL_EXCEL_PATH
from src.services.google_auth import get_google_services
from src.modules.job_agent.job_checker import check_job_active_status
from src.modules.job_agent.latex_tailor import generate_tailored_resume_pdf
from src.modules.job_agent.form_applier import generate_cover_letter_pitch, draft_job_application
from src.services.storage import update_local_excel

class JobApplicationAgent:
    def __init__(self, limit: int = 1):
        self.limit = limit
        self.sheets_service = None
        self.gmail_service = None

    def initialize_services(self):
        print("Initializing Google API services for Job Agent...")
        self.sheets_service, self.gmail_service = get_google_services()

    def run(self):
        if not self.sheets_service or not self.gmail_service:
            self.initialize_services()

        print(f"Fetching job listings from Google Sheet ({JOB_SPREADSHEET_ID})...")
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=JOB_SPREADSHEET_ID,
            range=f"{JOB_SHEET_NAME}!A2:G"
        ).execute()
        rows = result.get("values", [])

        processed_count = 0

        for idx, row in enumerate(rows, start=2):
            if processed_count >= self.limit:
                print(f"\nReached job application limit of {self.limit}. Stopping execution.")
                break

            job_title = row[0] if len(row) > 0 else ""
            company = row[1] if len(row) > 1 else ""
            tech_stack = row[2] if len(row) > 2 else ""
            location = row[3] if len(row) > 3 else ""
            job_url = row[4] if len(row) > 4 else ""
            date_posted = row[5] if len(row) > 5 else ""
            status = row[6] if len(row) > 6 else ""

            # Skip rows without job title or URL, or already processed
            if not job_title or not job_url or "Applied" in status or "Expired" in status:
                continue

            print(f"\n[{idx}] Processing Job: {job_title} @ {company}")
            print(f"-> Job URL: {job_url}")

            # 1. Check Job Active Status
            check_res = check_job_active_status(job_url)
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            if not check_res["is_active"]:
                print(f"-> Listing Inactive/Closed: {check_res['status_text']}")
                # Update Sheet status to Expired
                try:
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=JOB_SPREADSHEET_ID,
                        range=f"{JOB_SHEET_NAME}!G{idx}",
                        valueInputOption="RAW",
                        body={"values": [[f"Expired / Closed [{now_str}]"]]}
                    ).execute()
                except Exception as e:
                    print(f"Warning: Failed to update status in sheet: {e}")
                time.sleep(1.2)  # Rate limiting pause
                continue

            print("-> Job is Active. Tailoring LaTeX resume into Muhammad_Hamza_CV.pdf...")

            # 2. Tailor LaTeX Resume & Compile PDF
            pdf_path = generate_tailored_resume_pdf(
                job_title=job_title,
                company=company,
                tech_stack=tech_stack,
                job_desc=check_res["description"],
                output_filename="Muhammad_Hamza_CV.pdf"
            )
            print(f"-> Generated candidate resume: {pdf_path}")

            # 3. Generate Cover Letter & Draft Application in Gmail
            pitch = generate_cover_letter_pitch(job_title, company, tech_stack, check_res["description"])
            draft_id = draft_job_application(
                gmail_service=self.gmail_service,
                to_email="careers@" + company.lower().replace(" ", "").replace(",", "") + ".com",
                subject=pitch["subject"],
                body_text=pitch["body"],
                pdf_path=pdf_path
            )
            print(f"-> Application Draft created successfully in Gmail (ID: {draft_id})")

            # 4. Update Google Sheet Status (Column G)
            status_msg = f"Applied [{now_str}] (Draft ID: {draft_id})"
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=JOB_SPREADSHEET_ID,
                range=f"{JOB_SHEET_NAME}!G{idx}",
                valueInputOption="RAW",
                body={"values": [[status_msg]]}
            ).execute()

            # 5. Log to Local Excel
            update_local_excel(company, "careers@" + company + ".com", location, tech_stack, draft_id, pitch["subject"])
            print(f"-> Updated Google Sheet (Column G) & Local Excel Log ({LOCAL_EXCEL_PATH})")

            processed_count += 1
            time.sleep(1.2)

        print(f"\nFinished processing job batch. Total applications processed: {processed_count}")

def run_job_agent(limit: int = 1):
    agent = JobApplicationAgent(limit=limit)
    agent.run()
