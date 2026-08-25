import os
from dotenv import load_dotenv

load_dotenv()

def _get_env(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if not val:
        return default
    return val.strip(' "\'\t\r\n')

# Google Sheets Configuration
SPREADSHEET_ID = _get_env("SPREADSHEET_ID", "1OFy4ZgsUJsY0vwzdbHv-Lq6a6A1fagjb_8dbhX1y5pQ")
SHEET_NAME = _get_env("SHEET_NAME", "Sheet1")
JOB_SPREADSHEET_ID = _get_env("JOB_SPREADSHEET_ID", "11jBsR71XKX28rJkzjn1K6WvS5CIYzoRCRPPAYPVV03Y")
JOB_SHEET_NAME = _get_env("JOB_SHEET_NAME", SHEET_NAME)
EXPENSE_SPREADSHEET_ID = _get_env("EXPENSE_SPREADSHEET_ID", SPREADSHEET_ID)
EXPENSE_SHEET_NAME = _get_env("EXPENSE_SHEET_NAME", "Expenses")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
]

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = _get_env("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _get_env("TELEGRAM_CHAT_ID", "")

# Sender Information
SENDER_NAME = _get_env("SENDER_NAME", "Muhammad Hamza")
SENDER_PHONE = _get_env("SENDER_PHONE", "+92 327 1742800")
SENDER_PORTFOLIO = _get_env("SENDER_PORTFOLIO", "https://mrhamza.dev")
SENDER_ROLE = _get_env("SENDER_ROLE", "Full-Stack Web Developer")

# AI Model Configuration
GEMINI_API_KEY = _get_env("GEMINI_API_KEY", "")
AI_MODEL_NAME = _get_env("AI_MODEL_NAME", "gemini-3.5-flash")

# Storage & Credentials Paths
CREDENTIALS_FILE = _get_env("CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = _get_env("TOKEN_FILE", "token.json")
LOCAL_EXCEL_PATH = _get_env("LOCAL_EXCEL_PATH", "lead_outreach_log.xlsx")
EXPENSE_EXCEL_PATH = _get_env("EXPENSE_EXCEL_PATH", "expense_log.xlsx")
