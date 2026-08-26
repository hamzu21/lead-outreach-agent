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
import os

def send_gmail_message(gmail_service, to_email: str, subject: str, body_text: str, attachment_path: str = None) -> str:
    """
    Sends an email directly from the user's Gmail account with optional file attachment.
    """
    message = EmailMessage()
    message.set_content(body_text)
    message["To"] = to_email
    message["Subject"] = subject

    if attachment_path and os.path.exists(attachment_path):
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as f:
            file_data = f.read()
        
        subtype = "pdf" if filename.lower().endswith(".pdf") else "octet-stream"
        message.add_attachment(
            file_data,
            maintype="application",
            subtype=subtype,
            filename=filename
        )

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent_msg = gmail_service.users().messages().send(
        userId="me",
        body={"raw": encoded}
    ).execute()
    return sent_msg.get("id")

def trash_gmail_message(gmail_service, message_id_or_keyword: str) -> dict:
    """
    Moves matching email message to Gmail Trash bin by message ID or sender/keyword.
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service unavailable"}

    try:
        msg_id = message_id_or_keyword.strip()
        # If keyword instead of raw ID (e.g. 'duolingo' or 'newsletter')
        if " " in msg_id or len(msg_id) < 10 or "@" in msg_id:
            res = gmail_service.users().messages().list(
                userId="me",
                q=msg_id,
                maxResults=5
            ).execute()
            msgs = res.get("messages", [])
            if not msgs:
                return {"success": False, "error": f"No emails found matching '{message_id_or_keyword}'"}
            msg_id = msgs[0]["id"]

        # Move to Trash using Gmail API
        gmail_service.users().messages().trash(
            userId="me",
            id=msg_id
        ).execute()
        print(f"[GmailService] Trashed message ID: {msg_id}")
        return {"success": True, "msg_id": msg_id}
    except Exception as e:
        print(f"[GmailService] Error trashing email '{message_id_or_keyword}': {e}")
        return {"success": False, "error": str(e)}
