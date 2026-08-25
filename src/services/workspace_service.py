import os
import json

def make_file_shareable(drive_service, file_id: str, make_public: bool = False) -> str:
    """
    Returns the Google Drive webViewLink URL.
    By default (make_public=False), the file remains 100% PRIVATE to the owner account.
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
                fields='webViewLink, webContentLink'
            ).execute()
            return file_info.get("webViewLink", "")
    except Exception as e:
        print(f"[WorkspaceService] Warning getting file URL: {e}")
    return ""

def create_google_doc(docs_service, drive_service, title: str, content_text: str) -> dict:
    """
    Creates a new Google Doc, inserts formatted text content, and returns document URL.
    """
    if not docs_service:
        return {"success": False, "error": "Google Docs service unavailable"}

    try:
        # 1. Create document
        doc = docs_service.documents().create(body={"title": title}).execute()
        doc_id = doc.get("documentId")
        print(f"[WorkspaceService] Created Google Doc ID: {doc_id}")

        # 2. Insert content
        if content_text:
            requests = [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": content_text
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
