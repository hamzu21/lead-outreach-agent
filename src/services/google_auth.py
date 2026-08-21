import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from src.config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE

def get_google_services():
    """
    Authenticates and initializes Google Sheets and Gmail API services.
    Supports environment variables GOOGLE_CREDENTIALS_JSON and GOOGLE_TOKEN_JSON
    for headless execution environments such as GitHub Actions.
    """
    # Check if token content is provided via environment secret
    if not os.path.exists(TOKEN_FILE) and os.getenv("GOOGLE_TOKEN_JSON"):
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(os.getenv("GOOGLE_TOKEN_JSON"))

    # Check if credentials content is provided via environment secret
    if not os.path.exists(CREDENTIALS_FILE) and os.getenv("GOOGLE_CREDENTIALS_JSON"):
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            f.write(os.getenv("GOOGLE_CREDENTIALS_JSON"))

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Credentials file '{CREDENTIALS_FILE}' not found. "
                    "Please provide credentials.json or GOOGLE_CREDENTIALS_JSON environment variable."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    sheets_service = build("sheets", "v4", credentials=creds)
    gmail_service = build("gmail", "v1", credentials=creds)
    return sheets_service, gmail_service
