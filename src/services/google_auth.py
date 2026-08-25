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
    for headless execution environments such as AWS EC2 or GitHub Actions.
    """
    is_ci = os.getenv("CI") == "true" or bool(os.getenv("GITHUB_ACTIONS")) or os.getenv("AWS_EXECUTION_ENV") or True

    # 1. Sync TOKEN_FILE from environment variable if TOKEN_FILE does not exist
    token_env = os.getenv("GOOGLE_TOKEN_JSON", "").strip(' "\'\t\r\n')
    if token_env and token_env.startswith("{") and not os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(token_env)
        except Exception as e:
            print(f"[Google Auth] Warning writing TOKEN_FILE: {e}")

    # 2. Sync CREDENTIALS_FILE from environment variable if CREDENTIALS_FILE does not exist
    creds_env = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip(' "\'\t\r\n')
    if creds_env and creds_env.startswith("{") and not os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
                f.write(creds_env)
        except Exception as e:
            print(f"[Google Auth] Warning writing CREDENTIALS_FILE: {e}")

    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"[Google Auth] Error reading {TOKEN_FILE}: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[Google Auth] Refreshing expired Google OAuth credentials...")
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                print("[Google Auth] Credentials refreshed successfully.")
            except Exception as e:
                print(f"[Google Auth] Error refreshing Google OAuth token: {e}")
                creds = None
        
        if not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Credentials file '{CREDENTIALS_FILE}' not found and GOOGLE_CREDENTIALS_JSON not set."
                )
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"[Google Auth] Could not run browser OAuth flow: {e}")
                raise RuntimeError(
                    "Google OAuth credentials missing or expired on remote server! "
                    "Ensure GOOGLE_TOKEN_JSON and GOOGLE_CREDENTIALS_JSON are set in .env."
                )

    sheets_service = build("sheets", "v4", credentials=creds)
    gmail_service = build("gmail", "v1", credentials=creds)
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return sheets_service, gmail_service, docs_service, drive_service
