import os
from dotenv import load_dotenv

load_dotenv()

# Google Sheets Configuration
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1OFy4ZgsUJsY0vwzdbHv-Lq6a6A1fagjb_8dbhX1y5pQ")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.compose"
]

# Sender Information
SENDER_NAME = os.getenv("SENDER_NAME", "Muhammad Hamza")
SENDER_PHONE = os.getenv("SENDER_PHONE", "+92 327 1742800")
SENDER_PORTFOLIO = os.getenv("SENDER_PORTFOLIO", "https://mrhamza.dev")
SENDER_ROLE = os.getenv("SENDER_ROLE", "Full-Stack Web Developer")

# AI Model Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gemini-3.5-flash")

# Storage & Credentials Paths
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("TOKEN_FILE", "token.json")
LOCAL_EXCEL_PATH = os.getenv("LOCAL_EXCEL_PATH", "lead_outreach_log.xlsx")
