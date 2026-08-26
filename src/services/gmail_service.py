import base64
from email.message import EmailMessage
import os

def create_gmail_draft(gmail_service, to_email: str, subject: str, body_text: str, attachment_path: str = None) -> str:
    """
    Creates a draft email in the user's Gmail account with optional file attachment.
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
    draft = gmail_service.users().drafts().create(
        userId="me",
        body={"message": {"raw": encoded}}
    ).execute()
    return draft.get("id")

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

def check_matching_emails_count(gmail_service, keyword_or_query: str) -> dict:
    """
    Queries Gmail to count how many emails currently exist matching the given keyword/sender.
    Returns counts for active inbox/mail vs trash.
    """
    if not gmail_service:
        return {"success": False, "error": "Gmail service unavailable"}

    try:
        query_str = keyword_or_query.strip()
        # 1. Search in active Inbox / Mail (excluding trash)
        res_active = gmail_service.users().messages().list(
            userId="me",
            q=f"{query_str} -in:trash",
            maxResults=100
        ).execute()
        active_msgs = res_active.get("messages", [])

        # 2. Search in Trash
        res_trash = gmail_service.users().messages().list(
            userId="me",
            q=f"{query_str} in:trash",
            maxResults=100
        ).execute()
        trash_msgs = res_trash.get("messages", [])

        return {
            "success": True,
            "query": query_str,
            "active_count": len(active_msgs),
            "trash_count": len(trash_msgs),
            "total_count": len(active_msgs) + len(trash_msgs)
        }
    except Exception as e:
        print(f"[GmailService] Error checking email count for '{keyword_or_query}': {e}")
        return {"success": False, "error": str(e)}

def trash_gmail_message(gmail_service, message_id_or_keyword: str) -> dict:
    """
    Moves matching email message(s) to Gmail Trash bin by message ID or sender/keyword.
    Loops across ALL pages until 0 active emails remain for the query.
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
            return {"success": True, "msg_id": raw_input, "count": 1, "remaining": 0}

        # Otherwise, treat as keyword search query (e.g. 'freelancer', 'alibaba', 'duolingo', 'bayt.com')
        query_str = raw_input
        trashed_count = 0
        trashed_ids = []

        while True:
            res = gmail_service.users().messages().list(
                userId="me",
                q=f"{query_str} -in:trash",
                maxResults=100
            ).execute()
            msgs = res.get("messages", [])

            if not msgs and trashed_count == 0:
                # Fallback search query
                res = gmail_service.users().messages().list(
                    userId="me",
                    q=query_str,
                    maxResults=100
                ).execute()
                msgs = res.get("messages", [])

            if not msgs:
                break

            page_trashed = 0
            for m in msgs:
                m_id = m["id"]
                try:
                    gmail_service.users().messages().trash(userId="me", id=m_id).execute()
                    trashed_count += 1
                    page_trashed += 1
                    trashed_ids.append(m_id)
                except Exception as ex:
                    print(f"[GmailService] Notice trashing msg {m_id}: {ex}")

            if page_trashed == 0 or trashed_count >= 500:
                break

        # Verification count check after trashing
        res_check = gmail_service.users().messages().list(
            userId="me",
            q=f"{query_str} -in:trash",
            maxResults=10
        ).execute()
        remaining_count = len(res_check.get("messages", []))

        if trashed_count == 0:
            return {"success": False, "error": f"No active emails found matching '{message_id_or_keyword}' (0 remaining)."}

        print(f"[GmailService] Trashed total {trashed_count} emails for query '{query_str}'. Remaining: {remaining_count}")
        return {
            "success": True,
            "msg_id": trashed_ids[0] if trashed_ids else raw_input,
            "count": trashed_count,
            "remaining": remaining_count,
            "query": query_str
        }

    except Exception as e:
        print(f"[GmailService] Error trashing email '{message_id_or_keyword}': {e}")
        return {"success": False, "error": str(e)}
