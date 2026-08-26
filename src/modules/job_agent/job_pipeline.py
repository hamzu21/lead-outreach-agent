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
        self.sheets_service, self.gmail_service, _, _ = get_google_services()

    def run(self):
        if not self.sheets_service or not self.gmail_service:
            self.initialize_services()

        print(f"Fetching job listings from Google Sheet ({JOB_SPREADSHEET_ID})...")
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=JOB_SPREADSHEET_ID,
            range=f"{JOB_SHEET_NAME}!A1:H"
        ).execute()
        rows = result.get("values", [])

        if not rows:
            print("No job rows found in Google Sheet.")
            return

        # Locate header row containing 'Job Title'
        header_row_idx = 0
        offset = 0
        for i, r in enumerate(rows):
            if len(r) > 1 and "Job Title" in str(r[1]):
                header_row_idx = i
                offset = 1
                break
            elif len(r) > 0 and "Job Title" in str(r[0]):
                header_row_idx = i
                offset = 0
                break

        status_col_letter = "H" if offset == 1 else "G"
        processed_count = 0

        for idx_0, row in enumerate(rows[header_row_idx + 1:], start=header_row_idx + 2):
            if processed_count >= self.limit:
                print(f"\nReached job application limit of {self.limit}. Stopping execution.")
                break

            job_title = row[offset + 0] if len(row) > (offset + 0) else ""
            company = row[offset + 1] if len(row) > (offset + 1) else ""
            tech_stack = row[offset + 2] if len(row) > (offset + 2) else ""
            location = row[offset + 3] if len(row) > (offset + 3) else ""
            job_url = row[offset + 4] if len(row) > (offset + 4) else ""
            date_posted = row[offset + 5] if len(row) > (offset + 5) else ""
            status = row[offset + 6] if len(row) > (offset + 6) else ""

            # Skip invalid rows or already processed jobs
            if not job_title or job_title.strip() == "Job Title" or not job_url or "Applied" in status or "Expired" in status:
                continue

            print(f"\n[{idx_0}] Processing Job: {job_title} @ {company}")
            print(f"-> Job URL: {job_url}")

            # 1. Check Job Active Status
            check_res = check_job_active_status(job_url)
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            if not check_res["is_active"]:
                print(f"-> Listing Inactive/Closed: {check_res['status_text']}")
                try:
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=JOB_SPREADSHEET_ID,
                        range=f"{JOB_SHEET_NAME}!{status_col_letter}{idx_0}",
                        valueInputOption="RAW",
                        body={"values": [[f"Expired / Closed [{now_str}]"]]}
                    ).execute()
                except Exception as e:
                    print(f"Warning: Failed to update status in sheet: {e}")
                time.sleep(1.2)
                continue

            print("-> Job is Active. Tailoring native LaTeX resume to Muhammad_Hamza_CV.pdf...")

            # 2. Tailor LaTeX Resume & Compile PDF
            pdf_path = generate_tailored_resume_pdf(
                job_title=job_title,
                company=company,
                tech_stack=tech_stack,
                job_desc=check_res["description"],
                output_filename="Muhammad_Hamza_CV.pdf"
            )
            print(f"-> Generated native candidate resume: {pdf_path}")

            # 3. Generate Cover Letter & Draft Application in Gmail
            pitch = generate_cover_letter_pitch(job_title, company, tech_stack, check_res["description"])
            to_email = "careers@" + company.lower().replace(" ", "").replace(",", "") + ".com"
            draft_id = draft_job_application(
                gmail_service=self.gmail_service,
                to_email=to_email,
                subject=pitch["subject"],
                body_text=pitch["body"],
                pdf_path=pdf_path
            )
            print(f"-> Application Draft created successfully in Gmail (ID: {draft_id})")

            # 4. Update Google Sheet Status (Column H)
            status_msg = f"Applied [{now_str}] (Draft ID: {draft_id})"
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=JOB_SPREADSHEET_ID,
                range=f"{JOB_SHEET_NAME}!{status_col_letter}{idx_0}",
                valueInputOption="RAW",
                body={"values": [[status_msg]]}
            ).execute()

            # 5. Log to Local Excel Log
            update_local_excel(company, to_email, location, tech_stack, draft_id, pitch["subject"])
            print(f"-> Updated Google Sheet (Column {status_col_letter}) & Local Excel Log ({LOCAL_EXCEL_PATH})")

            processed_count += 1
            time.sleep(1.2)

        print(f"\nFinished processing job batch. Total applications processed: {processed_count}")

def run_job_agent(limit: int = 1):
    agent = JobApplicationAgent(limit=limit)
    agent.run()
