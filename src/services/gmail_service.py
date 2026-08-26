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
    Moves matching email message(s) to Gmail Trash bin by message ID or sender/keyword.
    If keyword, trashes ALL matching emails.
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service unavailable"}

    try:
        raw_input = message_id_or_keyword.strip()
        
        # Check if raw_input is a valid Gmail Hexadecimal Message ID (e.g. 1a03e4e9c1fe4332)
        is_hex_id = len(raw_input) >= 15 and all(c in "0123456789abcdefABCDEF" for c in raw_input)

        if is_hex_id:
            # Single exact Message ID trash
            gmail_service.users().messages().trash(userId="me", id=raw_input).execute()
            print(f"[GmailService] Trashed exact message ID: {raw_input}")
            return {"success": True, "msg_id": raw_input, "count": 1}

        # Otherwise, treat as keyword search query (e.g. 'freelancer', 'alibaba', 'duolingo')
        query_str = raw_input
        res = gmail_service.users().messages().list(
            userId="me",
            q=query_str,
            maxResults=50
        ).execute()
        msgs = res.get("messages", [])

        if not msgs:
            # Fallback search query
            res = gmail_service.users().messages().list(
                userId="me",
                q=f"from:{query_str} OR {query_str}",
                maxResults=50
            ).execute()
            msgs = res.get("messages", [])

        if not msgs:
            return {"success": False, "error": f"No emails found matching '{message_id_or_keyword}'"}

        trashed_count = 0
        trashed_ids = []
        for m in msgs:
            m_id = m["id"]
            try:
                gmail_service.users().messages().trash(userId="me", id=m_id).execute()
                trashed_count += 1
                trashed_ids.append(m_id)
            except Exception as ex:
                print(f"[GmailService] Warning trashing msg {m_id}: {ex}")

        print(f"[GmailService] Trashed {trashed_count} emails for query '{query_str}'")
        return {
            "success": True,
            "msg_id": trashed_ids[0] if trashed_ids else raw_input,
            "count": trashed_count,
            "query": query_str
        }

    except Exception as e:
        print(f"[GmailService] Error trashing email '{message_id_or_keyword}': {e}")
        return {"success": False, "error": str(e)}
