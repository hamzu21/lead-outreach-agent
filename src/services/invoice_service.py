import os
import json
import datetime
from src.services.workspace_service import create_google_doc, create_styled_spreadsheet, update_spreadsheet_data

def generate_invoice_number() -> str:
    """Generates a clean timestamped invoice ID like INV-20260825-101"""
    now = datetime.datetime.now()
    return f"INV-{now.strftime('%Y%m%d')}-{now.strftime('%H%M')}"

def create_client_invoice(docs_service, sheets_service, drive_service, client_name: str, amount: str, currency: str = "USD", description: str = "Software Development Services", client_email: str = "") -> dict:
    """
    Creates a professional Invoice document in Google Docs, logs billing metadata in a Google Sheet,
    and returns document links.
    """
    invoice_num = generate_invoice_number()
    issue_date = datetime.datetime.now().strftime("%B %d, %Y")
    due_date = (datetime.datetime.now() + datetime.timedelta(days=14)).strftime("%B %d, %Y")
    
    clean_amt = str(amount).replace("$", "").replace("USD", "").replace("PKR", "").replace("RS", "").strip()
    if not clean_amt:
        clean_amt = "500"

    curr_symbol = "$" if currency.upper() in ["USD", "$"] else ("PKR " if currency.upper() in ["PKR", "RS"] else f"{currency} ")
    formatted_amount = f"{curr_symbol}{clean_amt}"

    invoice_text = f"""
================================================================================
                                INVOICE
================================================================================

Invoice Number : {invoice_num}
Issue Date     : {issue_date}
Payment Due    : {due_date}

--------------------------------------------------------------------------------
BILLED TO:
Client Name    : {client_name}
Client Email   : {client_email if client_email else 'N/A'}

BILLED BY:
Muhammad Hamza (Full-Stack & AI Solutions Developer)
Email          : misterhamza117@gmail.com
--------------------------------------------------------------------------------

ITEM DESCRIPTION                                           AMOUNT
--------------------------------------------------------------------------------
{description:<58} {formatted_amount}

--------------------------------------------------------------------------------
TOTAL AMOUNT DUE:                                         {formatted_amount}
--------------------------------------------------------------------------------

PAYMENT INSTRUCTIONS:
• Bank / Wire Transfer, Payoneer, or Wise accepted.
• Please send confirmation receipt to misterhamza117@gmail.com once processed.

Thank you for your business!
================================================================================
"""

    title = f"Invoice {invoice_num} - {client_name}"

    # 1. Create Invoice Google Doc
    doc_res = create_google_doc(docs_service, drive_service, title=title, content_text=invoice_text)
    if not doc_res.get("success"):
        return {"success": False, "error": f"Failed to create Google Doc invoice: {doc_res.get('error')}"}

    doc_url = doc_res.get("url")

    # 2. Log in "Client Billing & Invoices" Google Sheet
    sheet_row = [
        invoice_num,
        client_name,
        client_email if client_email else "N/A",
        f"{curr_symbol}{amount}",
        description,
        issue_date,
        due_date,
        "UNPAID",
        doc_url
    ]

    try:
        # Search for existing billing sheet or create one
        search_res = drive_service.files().list(
            q="name = 'Client Billing & Invoices' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
            fields="files(id)"
        ).execute() if drive_service else {}
        
        files = search_res.get("files", [])
        if files:
            spreadsheet_id = files[0]["id"]
            update_spreadsheet_data(sheets_service, spreadsheet_id, "Sheet1!A:I", [sheet_row])
        else:
            headers = ["Invoice #", "Client Name", "Client Email", "Amount", "Description", "Issue Date", "Due Date", "Status", "Doc Link"]
            create_styled_spreadsheet(
                sheets_service,
                drive_service,
                title="Client Billing & Invoices",
                headers=headers,
                rows=[sheet_row],
                theme_color="green"
            )
    except Exception as e:
        print(f"[InvoiceService] Warning logging to billing sheet: {e}")

    return {
        "success": True,
        "invoice_number": invoice_num,
        "title": title,
        "client_name": client_name,
        "amount": formatted_amount,
        "doc_url": doc_url,
        "issue_date": issue_date,
        "due_date": due_date
    }
