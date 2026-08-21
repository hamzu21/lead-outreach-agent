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
    is_ci = os.getenv("CI") == "true" or bool(os.getenv("GITHUB_ACTIONS"))

    # Write TOKEN_FILE from secret if provided
    token_env = os.getenv("GOOGLE_TOKEN_JSON")
    if token_env and not os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token_env.strip())

    # Write CREDENTIALS_FILE from secret if provided
    creds_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_env and not os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            f.write(creds_env.strip())

    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Error reading {TOKEN_FILE}: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired Google OAuth credentials...")
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Error refreshing Google OAuth token: {e}")
                creds = None
        
        if not creds or not creds.valid:
            if is_ci:
                raise RuntimeError(
                    "Google OAuth credentials missing or invalid in GitHub Actions! "
                    "Please ensure GOOGLE_TOKEN_JSON and GOOGLE_CREDENTIALS_JSON secrets are set in repository settings."
                )
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Credentials file '{CREDENTIALS_FILE}' not found. "
                    "Please provide credentials.json or set GOOGLE_CREDENTIALS_JSON environment variable."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

    sheets_service = build("sheets", "v4", credentials=creds)
    gmail_service = build("gmail", "v1", credentials=creds)
    return sheets_service, gmail_service
