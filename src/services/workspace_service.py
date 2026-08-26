import os
import json

def make_file_shareable(drive_service, file_id: str, make_public: bool = True) -> str:
    """
    Sets Google Drive permissions to 'anyone' with 'writer' role so anyone with the link can open and edit immediately.
    Returns the shareable Google Drive webViewLink URL.
    """
    try:
        if drive_service:
            if make_public:
                permission = {
                    'type': 'anyone',
                    'role': 'writer',
                }
                drive_service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    fields='id',
                ).execute()

            file_info = drive_service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            url = file_info.get("webViewLink", "")
            if url:
                return url
    except Exception as e:
        print(f"[WorkspaceService] Warning getting file URL: {e}")
    return f"https://docs.google.com/spreadsheets/d/{file_id}/edit?usp=sharing"

from src.services.formatting_cleaner import clean_text_for_doc

def create_google_doc(docs_service, drive_service, title: str, content_text: str) -> dict:
    """
    Creates a new Google Doc, inserts clean formatted text content without raw markdown symbols, and returns document URL.
    """
    if not docs_service:
        return {"success": False, "error": "Google Docs service unavailable"}

    cleaned_content = clean_text_for_doc(content_text)

    try:
        # 1. Create document
        doc = docs_service.documents().create(body={"title": title}).execute()
        doc_id = doc.get("documentId")
        print(f"[WorkspaceService] Created Google Doc ID: {doc_id}")

        # 2. Insert content
        if cleaned_content:
            requests = [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": cleaned_content
                    }
                }
            ]
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests}
            ).execute()

        # 3. Make shareable and get web URL
        share_url = make_file_shareable(drive_service, doc_id)
        if not share_url:
            share_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        return {
            "success": True,
            "doc_id": doc_id,
            "url": share_url,
            "title": title
        }
    except Exception as e:
        print(f"[WorkspaceService] Error creating Google Doc: {e}")
        return {"success": False, "error": str(e)}

def update_google_doc(docs_service, doc_id: str, append_text: str) -> dict:
    """
    Appends text content to an existing Google Doc.
    """
    if not docs_service:
        return {"success": False, "error": "Google Docs service unavailable"}

    try:
        # Fetch doc to get current length
        doc = docs_service.documents().get(documentId=doc_id).execute()
        body_content = doc.get("body", {}).get("content", [])
        end_index = 1
        if body_content:
            end_index = body_content[-1].get("endIndex", 1) - 1

        requests = [
            {
                "insertText": {
                    "location": {"index": max(1, end_index)},
                    "text": f"\n\n{append_text}"
                }
            }
        ]
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests}
        ).execute()

        url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return {"success": True, "doc_id": doc_id, "url": url}
    except Exception as e:
        print(f"[WorkspaceService] Error updating Google Doc {doc_id}: {e}")
        return {"success": False, "error": str(e)}

def create_styled_spreadsheet(sheets_service, drive_service, title: str, headers: list, rows: list, theme_color: str = "blue") -> dict:
    """
    Creates a styled Google Sheet with colored headers, bold white text, populated data,
    and returns shareable spreadsheet URL.
    """
    if not sheets_service:
        return {"success": False, "error": "Google Sheets service unavailable"}

    try:
        # 1. Create spreadsheet
        spreadsheet_body = {
            "properties": {"title": title}
        }
        spreadsheet = sheets_service.spreadsheets().create(
            body=spreadsheet_body,
            fields="spreadsheetId"
        ).execute()
        spreadsheet_id = spreadsheet.get("spreadsheetId")
        print(f"[WorkspaceService] Created Google Sheet ID: {spreadsheet_id}")

        # 2. Append Headers and Rows
        all_values = []
        if headers:
            all_values.append(headers)
        if rows:
            all_values.extend(rows)

        if all_values:
            value_body = {"values": all_values}
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A1",
                valueInputOption="USER_ENTERED",
                body=value_body
            ).execute()

        # 3. Apply Styling (Header color, bold font, freeze top row)
        # Theme RGB colors
        rgb_color = {"red": 0.1, "green": 0.45, "blue": 0.91} # Default Blue
        if theme_color.lower() == "green":
            rgb_color = {"red": 0.06, "green": 0.62, "blue": 0.35}
        elif theme_color.lower() == "purple":
            rgb_color = {"red": 0.55, "green": 0.23, "blue": 0.85}

        format_requests = [
            # Freeze header row
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 0,
                        "gridProperties": {"frozenRowCount": 1}
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            },
            # Style Header Row (Background color, white bold text, center alignment)
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": rgb_color,
                            "textFormat": {
                                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                                "bold": True,
                                "fontSize": 11
                            },
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            }
        ]

        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": format_requests}
        ).execute()

        # 4. Make shareable and get web URL
        share_url = make_file_shareable(drive_service, spreadsheet_id)
        if not share_url:
            share_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

        return {
            "success": True,
            "spreadsheet_id": spreadsheet_id,
            "url": share_url,
            "title": title
        }
    except Exception as e:
        print(f"[WorkspaceService] Error creating Google Sheet: {e}")
        return {"success": False, "error": str(e)}

def create_professional_finance_spreadsheet(sheets_service, drive_service, title: str = "Personal Finance Tracker - Muhammad Hamza") -> dict:
    """
    Creates a multi-tab Executive Personal Finance & Budgeting OS Google Sheet containing:
    1. 📊 Executive Dashboard (SUM Formulas for Net Savings, Total Income, Expenses, Udhaar)
    2. 💸 Expenses Log (Categories, Amounts, Methods, Total Row)
    3. 💰 Income Log (Clients, Sources, Amounts, Total Row)
    4. 🤝 Udhaar & Loans Tracker (Lent/Borrowed, Due Dates, Outstanding Total)
    """
    if not sheets_service:
        return {"success": False, "error": "Google Sheets service unavailable"}

    try:
        spreadsheet_body = {
            "properties": {"title": title},
            "sheets": [
                {"properties": {"sheetId": 0, "title": "📊 Executive Dashboard", "gridProperties": {"frozenRowCount": 2, "rowCount": 30, "columnCount": 10}}},
                {"properties": {"sheetId": 1, "title": "💸 Expenses Log", "gridProperties": {"frozenRowCount": 1, "rowCount": 50, "columnCount": 10}}},
                {"properties": {"sheetId": 2, "title": "💰 Income Log", "gridProperties": {"frozenRowCount": 1, "rowCount": 50, "columnCount": 10}}},
                {"properties": {"sheetId": 3, "title": "🤝 Udhaar & Loans Tracker", "gridProperties": {"frozenRowCount": 1, "rowCount": 50, "columnCount": 10}}}
            ]
        }
        sp = sheets_service.spreadsheets().create(body=spreadsheet_body, fields="spreadsheetId").execute()
        spreadsheet_id = sp.get("spreadsheetId")
        print(f"[WorkspaceService] Created Executive Finance Sheet ID: {spreadsheet_id}")

        dash_values = [
            ["PERSONAL FINANCE EXECUTIVE DASHBOARD - MUHAMMAD HAMZA", "", "", ""],
            ["Metric Key", "Value (PKR / USD)", "Calculation Formula / Source", "Notes"],
            ["Total Income & Revenue", "=SUM('💰 Income Log'!D2:D50)", "=SUM('💰 Income Log'!D2:D50)", "Auto-calculated from Income Log tab"],
            ["Total Expenses & Spending", "=SUM('💸 Expenses Log'!D2:D50)", "=SUM('💸 Expenses Log'!D2:D50)", "Auto-calculated from Expenses Log tab"],
            ["Net Savings / Cash Balance", "=B3-B4", "Income minus Expenses", "Current Net Savings"],
            ["Total Udhaar Given (Lent to others)", "=SUMIF('🤝 Udhaar & Loans Tracker'!C2:C50, \"Udhaar Given (Lent)\", '🤝 Udhaar & Loans Tracker'!D2:D50)", "Sum of Money Lent to Friends/Clients", "Receivable Money"],
            ["Total Udhaar Taken (Borrowed from others)", "=SUMIF('🤝 Udhaar & Loans Tracker'!C2:C50, \"Udhaar Taken (Borrowed)\", '🤝 Udhaar & Loans Tracker'!D2:D50)", "Sum of Money Borrowed from Others", "Payable Debt"]
        ]

        exp_values = [
            ["Date", "Category", "Description", "Amount (PKR)", "Payment Method", "Status", "Notes"],
            ["2026-08-01", "Groceries & Food", "Weekly supermarket groceries", 15500, "Bank Transfer", "Paid", "Weekly essentials"],
            ["2026-08-05", "Utilities & Bills", "K-Electric electricity bill", 24800, "Online Banking", "Paid", "Monthly electricity"],
            ["2026-08-10", "Fuel & Transport", "Car fuel tank refill", 12000, "Credit Card", "Paid", "Full tank petrol"],
            ["2026-08-15", "Tech & Subscriptions", "Vercel / OpenAI API sub", 8500, "Credit Card", "Paid", "SaaS tools"],
            ["2026-08-20", "Dining Out & Personal", "Dinner with clients", 9200, "Cash", "Paid", "Business meeting"],
            ["TOTAL EXPENSES", "", "", "=SUM(D2:D6)", "", "", "Auto Total"]
        ]

        inc_values = [
            ["Date", "Source / Client Name", "Income Category", "Amount (PKR)", "Payment Method", "Notes"],
            ["2026-08-01", "Full-Stack Retainer", "Monthly Client Retainer", 350000, "Bank Transfer", "Fixed monthly retainer"],
            ["2026-08-12", "Upwork Project", "AI Agent Development", 185000, "Payoneer", "Project milestone"],
            ["2026-08-22", "Web Consultation", "Architecture Audit", 75000, "Direct Deposit", "One-time consultation"],
            ["TOTAL INCOME", "", "", "=SUM(D2:D4)", "", "Auto Total"]
        ]

        udhaar_values = [
            ["Date", "Person Name", "Transaction Type", "Amount (PKR)", "Due Date", "Status", "Notes"],
            ["2026-08-03", "Ali Ahmed", "Udhaar Given (Lent)", 25000, "2026-09-01", "Pending", "Lent for emergency"],
            ["2026-08-14", "Tech Vendor", "Udhaar Taken (Borrowed)", 15000, "2026-08-30", "Pending", "Hardware purchase due"],
            ["TOTAL UDHAAR OUTSTANDING", "", "", "=SUM(D2:D3)", "", "", "Auto Total"]
        ]

        data_updates = [
            {"range": "'📊 Executive Dashboard'!A1", "values": dash_values},
            {"range": "'💸 Expenses Log'!A1", "values": exp_values},
            {"range": "'💰 Income Log'!A1", "values": inc_values},
            {"range": "'🤝 Udhaar & Loans Tracker'!A1", "values": udhaar_values}
        ]

        sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data_updates}
        ).execute()

        # Format Headers (Royal Blue Header)
        rgb_color = {"red": 0.11, "green": 0.22, "blue": 0.54} # Deep Royal Blue
        format_requests = [
            # Dashboard Title Row 1
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": rgb_color,
                            "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12},
                            "horizontalAlignment": "LEFT"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            },
            # Dashboard Table Headers Row 2
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 2},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.94, "green": 0.96, "blue": 0.98},
                            "textFormat": {"foregroundColor": {"red": 0.05, "green": 0.09, "blue": 0.16}, "bold": True, "fontSize": 10},
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            }
        ]

        try:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": format_requests}
            ).execute()
        except Exception as fe:
            print(f"[WorkspaceService] Format warning: {fe}")

        share_url = make_file_shareable(drive_service, spreadsheet_id, make_public=True)
        return {
            "success": True,
            "spreadsheet_id": spreadsheet_id,
            "url": share_url,
            "title": title
        }
    except Exception as e:
        print(f"[WorkspaceService] Error creating professional finance spreadsheet: {e}")
        return {"success": False, "error": str(e)}

def update_spreadsheet_data(sheets_service, spreadsheet_id: str, range_name: str, rows: list) -> dict:
    """
    Appends data rows to an existing Google Sheet.
    """
    if not sheets_service:
        return {"success": False, "error": "Google Sheets service unavailable"}

    try:
        body = {"values": rows}
        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name or "Sheet1!A:Z",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        return {"success": True, "spreadsheet_id": spreadsheet_id, "url": url}
    except Exception as e:
        print(f"[WorkspaceService] Error updating Google Sheet {spreadsheet_id}: {e}")
        return {"success": False, "error": str(e)}

def trash_drive_file(drive_service, file_identifier: str) -> dict:
    """
    Finds a Google Drive file by ID or title and moves it to Trash.
    """
    if not drive_service:
        return {"success": False, "error": "Google Drive service unavailable"}

    try:
        target_id = file_identifier.strip()
        target_name = file_identifier

        # If file_identifier is not a direct ID (IDs are ~33-44 alphanum chars without spaces)
        if " " in target_id or len(target_id) < 20 or "/" in target_id:
            query = f"name contains '{target_id}' and trashed = false"
            res = drive_service.files().list(q=query, fields="files(id, name)").execute()
            files = res.get("files", [])
            if not files:
                return {"success": False, "error": f"No active Google Drive file found matching '{file_identifier}'"}
            target_id = files[0]["id"]
            target_name = files[0]["name"]

        drive_service.files().update(
            fileId=target_id,
            body={"trashed": True}
        ).execute()
        print(f"[WorkspaceService] Trashed Google Drive file ID: {target_id}")

        return {"success": True, "file_id": target_id, "file_name": target_name}
    except Exception as e:
        print(f"[WorkspaceService] Error trashing file '{file_identifier}': {e}")
        return {"success": False, "error": str(e)}

def list_workspace_files(drive_service, file_type: str = "all") -> dict:
    """
    Lists Google Drive spreadsheets and/or documents with title, mimeType, and web links.
    """
    if not drive_service:
        return {"success": False, "error": "Google Drive service unavailable"}

    try:
        q_parts = ["trashed = false"]
        if file_type.lower() in ["spreadsheet", "sheets", "excel"]:
            q_parts.append("mimeType = 'application/vnd.google-apps.spreadsheet'")
        elif file_type.lower() in ["document", "docs", "doc"]:
            q_parts.append("mimeType = 'application/vnd.google-apps.document'")
        else:
            q_parts.append("(mimeType = 'application/vnd.google-apps.spreadsheet' or mimeType = 'application/vnd.google-apps.document')")

        query = " and ".join(q_parts)
        res = drive_service.files().list(
            q=query,
            pageSize=25,
            fields="files(id, name, mimeType, webViewLink, createdTime)"
        ).execute()

        files = res.get("files", [])
        return {"success": True, "files": files}
    except Exception as e:
        print(f"[WorkspaceService] Error listing Drive files: {e}")
        return {"success": False, "error": str(e)}

def find_drive_file_by_name(drive_service, keyword: str, file_type: str = "spreadsheet") -> dict:
    """
    Searches user's Google Drive Cloud for a spreadsheet or document matching keyword in title.
    Returns dict with file_id, file_name, url.
    """
    if not drive_service or not keyword:
        return {}

    try:
        clean_kw = keyword.replace("'", "\\'").strip()
        mime = "application/vnd.google-apps.spreadsheet" if "sheet" in file_type.lower() else "application/vnd.google-apps.document"
        query = f"name contains '{clean_kw}' and trashed = false and mimeType = '{mime}'"
        
        res = drive_service.files().list(
            q=query,
            pageSize=5,
            fields="files(id, name, mimeType, webViewLink, modifiedTime)"
        ).execute()

        files = res.get("files", [])
        if not files:
            query_any = f"name contains '{clean_kw}' and trashed = false"
            res_any = drive_service.files().list(
                q=query_any,
                pageSize=5,
                fields="files(id, name, mimeType, webViewLink, modifiedTime)"
            ).execute()
            files = res_any.get("files", [])

        if files:
            best_file = files[0]
            print(f"[WorkspaceService] Found matching Drive file by name '{keyword}': '{best_file.get('name')}' (ID: {best_file.get('id')})")
            return {
                "file_id": best_file.get("id"),
                "file_name": best_file.get("name"),
                "url": best_file.get("webViewLink")
            }
    except Exception as e:
        print(f"[WorkspaceService] Error finding Drive file by name '{keyword}': {e}")
    return {}

def clear_and_update_finance_sheet(sheets_service, drive_service, file_identifier: str, starting_balance: float = None) -> dict:
    """
    Finds a Google Sheet by title keyword or ID, clears all mock data rows from Expenses, Income, and Udhaar tabs,
    updates starting bank balance if provided, and returns the updated sheet link.
    """
    if not sheets_service or not drive_service:
        return {"success": False, "error": "Google Sheets service unavailable"}

    try:
        # Find file_id
        target_id = file_identifier.strip()
        target_name = file_identifier

        if " " in target_id or len(target_id) < 20 or "/" in target_id:
            found = find_drive_file_by_name(drive_service, file_identifier, file_type="spreadsheet")
            if not found:
                # If no matching sheet by keyword, pick the most recently modified spreadsheet
                res_recent = drive_service.files().list(
                    q="mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
                    orderBy="modifiedTime desc",
                    pageSize=1,
                    fields="files(id, name, webViewLink)"
                ).execute()
                r_files = res_recent.get("files", [])
                if r_files:
                    target_id = r_files[0]["id"]
                    target_name = r_files[0]["name"]
                else:
                    return {"success": False, "error": f"No active Google Sheet found matching '{file_identifier}'"}
            else:
                target_id = found["file_id"]
                target_name = found["file_name"]

        # Get Sheet Metadata Tabs
        meta = sheets_service.spreadsheets().get(spreadsheetId=target_id).execute()
        sheet_tabs = [s['properties']['title'] for s in meta.get('sheets', [])]
        try:
            print(f"[WorkspaceService] Clearing mock data from Google Sheet '{target_name}' (ID: {target_id}).")
        except Exception:
            pass

        # Clear data rows from Expenses Log, Income Log, Udhaar Tracker
        for tab in sheet_tabs:
            if "dashboard" in tab.lower() or "summary" in tab.lower():
                continue
            clear_range = f"'{tab}'!A2:Z100"
            try:
                sheets_service.spreadsheets().values().clear(
                    spreadsheetId=target_id,
                    range=clear_range,
                    body={}
                ).execute()
                print(f"-> Cleared data rows from tab '{tab.encode('ascii', errors='ignore').decode()}'")
            except Exception as ce:
                print(f"Warning clearing tab: {ce}")

        # Update Starting Balance on Executive Dashboard / Summary if tab exists
        dash_tab = None
        for tab in sheet_tabs:
            if "dashboard" in tab.lower() or "summary" in tab.lower() or "setup" in tab.lower():
                dash_tab = tab
                break

        if dash_tab and starting_balance is not None:
            balance_row = [["Starting Bank Balance / Cash Reserve", starting_balance, "Initial Starting Balance", "Configured by user"]]
            try:
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=target_id,
                    range=f"'{dash_tab}'!A3:D3",
                    valueInputOption="USER_ENTERED",
                    body={"values": balance_row}
                ).execute()
                print(f"-> Updated starting bank balance to {starting_balance}")
            except Exception as be:
                print(f"Warning updating balance: {be}")

        share_url = make_file_shareable(drive_service, target_id, make_public=True)
        return {
            "success": True,
            "spreadsheet_id": target_id,
            "title": target_name,
            "starting_balance": starting_balance,
            "url": share_url
        }
    except Exception as e:
        print(f"[WorkspaceService] Error clearing and updating finance sheet: {str(e).encode('ascii', errors='ignore').decode()}")
        return {"success": False, "error": str(e)}
