import os
import json
import base64
from email.message import EmailMessage
from src.config import SENDER_NAME, SENDER_PORTFOLIO, SENDER_PHONE
from src.services.ai_generator import generate_ai_content

def generate_cover_letter_pitch(job_title: str, company: str, tech_stack: str, job_desc: str) -> dict:
    """
    Generates a personalized cover letter pitch and subject line using Gemini AI.
    """
    prompt = f"""
You are drafting a professional, high-converting job application email for Muhammad Hamza ({SENDER_PORTFOLIO}).

Job Details:
- Role Title: {job_title}
- Company Name: {company}
- Core Tech Stack: {tech_stack}
- Job Description snippet: {job_desc[:1500]}

Candidate Info:
- Name: {SENDER_NAME}
- Role: Full-Stack Web Developer (Pakistan)
- Phone: {SENDER_PHONE}
- Portfolio: {SENDER_PORTFOLIO}

Requirements:
1. Subject line: Clear and direct (e.g., "Application for {job_title} - Muhammad Hamza").
2. Email Body:
   - Concise, compelling cover letter (3 short paragraphs).
   - Address why Muhammad Hamza is a strong technical fit for {job_title} at {company}.
   - Mention key experience matching {tech_stack}.
   - Include portfolio link ({SENDER_PORTFOLIO}) and state that tailored CV is attached as Muhammad_Hamza_CV.pdf.

Output Format (strict JSON):
{{
  "subject": "Application Subject Line",
  "body": "Cover letter body text"
}}
"""
    raw_res = generate_ai_content(prompt, response_mime_type="application/json")
    return json.loads(raw_res)

def draft_job_application(gmail_service, to_email: str, subject: str, body_text: str, pdf_path: str = "Muhammad_Hamza_CV.pdf") -> str:
    """
    Drafts an application email in Gmail with Muhammad_Hamza_CV.pdf attached.
    """
    message = EmailMessage()
    message.set_content(body_text)
    message["To"] = to_email if to_email and "@" in to_email else "careers@company.com"
    message["Subject"] = subject

    # Attach tailored PDF resume
    if pdf_path and os.path.exists(pdf_path):
        filename = "Muhammad_Hamza_CV.pdf"
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        message.add_attachment(
            pdf_data,
            maintype="application",
            subtype="pdf",
            filename=filename
        )

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = gmail_service.users().drafts().create(
        userId="me",
        body={"message": {"raw": encoded}}
    ).execute()

    return draft.get("id")
