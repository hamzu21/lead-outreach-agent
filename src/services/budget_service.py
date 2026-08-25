import json
from src.services.ai_generator import generate_ai_content
from src.services.time_utils import get_pkt_now_str

def generate_financial_health_report(sheets_service, drive_service) -> str:
    """
    Reads logged expenses and billed invoices, calculates total financial health,
    savings rates, spending alerts, and returns an executive financial report.
    """
    current_time_str = get_pkt_now_str()

    # Search for expense and billing spreadsheets in Drive
    expense_files = []
    billing_files = []
    try:
        if drive_service:
            res_exp = drive_service.files().list(
                q="name = 'Expense Log' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
                fields="files(id)"
            ).execute()
            expense_files = res_exp.get("files", [])

            res_bill = drive_service.files().list(
                q="name = 'Client Billing & Invoices' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
                fields="files(id)"
            ).execute()
            billing_files = res_bill.get("files", [])
    except Exception as e:
        print(f"[BudgetService] Warning querying Drive: {e}")

    # Read expense spreadsheet rows if available
    expense_rows = []
    if sheets_service and expense_files:
        try:
            exp_data = sheets_service.spreadsheets().values().get(
                spreadsheetId=expense_files[0]["id"],
                range="Sheet1!A:F"
            ).execute()
            expense_rows = exp_data.get("values", [])
        except Exception as e:
            print(f"[BudgetService] Warning reading expenses: {e}")

    # Read billing spreadsheet rows if available
    billing_rows = []
    if sheets_service and billing_files:
        try:
            bill_data = sheets_service.spreadsheets().values().get(
                spreadsheetId=billing_files[0]["id"],
                range="Sheet1!A:I"
            ).execute()
            billing_rows = bill_data.get("values", [])
        except Exception as e:
            print(f"[BudgetService] Warning reading billing: {e}")

    prompt = f"""
You are Zeyra, an executive Personal Financial Director analyzing Muhammad Hamza's financial health.

Current Date (PKT): {current_time_str}
Logged Expense Rows: {json.dumps(expense_rows[:15]) if expense_rows else 'No logged expense rows yet'}
Client Billing Rows: {json.dumps(billing_rows[:15]) if billing_rows else 'No billing invoice rows yet'}

Generate a crisp, structured Personal Financial Health Report:
1. 💰 *Income vs Expense Overview* (Summarize revenue from client invoices vs total expenses).
2. 📊 *Category Spending Insights* (Food, Tech/Server costs, Utilities, Personal).
3. ⚠️ *Budget Alerts & Savings Rate Advice* (Proactive recommendations to optimize monthly net savings).

Format in clean Telegram Markdown.
"""
    report = generate_ai_content(prompt)
    return report
