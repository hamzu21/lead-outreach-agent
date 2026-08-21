import base64
from email.message import EmailMessage

def create_gmail_draft(gmail_service, to_email: str, subject: str, body_text: str) -> str:
    """
    Creates a draft email in the user's Gmail account.
    """
    message = EmailMessage()
    message.set_content(body_text)
    message["To"] = to_email
    message["Subject"] = subject

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = gmail_service.users().drafts().create(
        userId="me",
        body={"message": {"raw": encoded}}
    ).execute()
    return draft.get("id")
