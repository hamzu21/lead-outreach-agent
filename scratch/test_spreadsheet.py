import sys
import os
sys.path.append(".")
import json
from src.services.google_auth import get_google_services

sheets, gmail, docs, drive = get_google_services()

print("--- TESTING MULTI-TAB GOOGLE SHEET CREATION ---")

spreadsheet_body = {
    'properties': {'title': 'Personal Finance Tracker & OS - Muhammad Hamza'},
    'sheets': [
        {'properties': {'sheetId': 0, 'title': 'Dashboard', 'gridProperties': {'frozenRowCount': 2, 'rowCount': 30, 'columnCount': 10}}},
        {'properties': {'sheetId': 1, 'title': 'Expenses Log', 'gridProperties': {'frozenRowCount': 1, 'rowCount': 50, 'columnCount': 10}}},
        {'properties': {'sheetId': 2, 'title': 'Income Log', 'gridProperties': {'frozenRowCount': 1, 'rowCount': 50, 'columnCount': 10}}},
        {'properties': {'sheetId': 3, 'title': 'Udhaar & Loans Tracker', 'gridProperties': {'frozenRowCount': 1, 'rowCount': 50, 'columnCount': 10}}}
    ]
}

sp = sheets.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId').execute()
sp_id = sp.get('spreadsheetId')
print('Spreadsheet Created! ID:', sp_id)

dash_values = [
    ['PERSONAL FINANCE EXECUTIVE DASHBOARD - MUHAMMAD HAMZA', '', '', ''],
    ['Metric Key', 'Value (PKR)', 'Formula / Source', 'Notes'],
    ['Total Income & Revenue', "=SUM('Income Log'!D2:D50)", "=SUM('Income Log'!D2:D50)", 'Auto-calculated from Income Log tab'],
    ['Total Expenses & Spending', "=SUM('Expenses Log'!D2:D50)", "=SUM('Expenses Log'!D2:D50)", 'Auto-calculated from Expenses Log tab'],
    ['Net Savings / Cash Balance', "=B3-B4", "Income minus Expenses", "Current Net Balance"],
    ['Total Udhaar Given (Lent)', "=SUMIF('Udhaar & Loans Tracker'!C2:C50, \"Udhaar Given (Lent)\", 'Udhaar & Loans Tracker'!D2:D50)", "Money Lent to Friends/Clients", "Receivable Debt"],
    ['Total Udhaar Taken (Borrowed)', "=SUMIF('Udhaar & Loans Tracker'!C2:C50, \"Udhaar Taken (Borrowed)\", 'Udhaar & Loans Tracker'!D2:D50)", "Money Borrowed from Others", "Payable Debt"]
]

exp_values = [
    ['Date', 'Category', 'Description', 'Amount (PKR)', 'Payment Method', 'Status', 'Notes'],
    ['2026-08-01', 'Groceries & Food', 'Weekly supermarket groceries', 15500, 'Bank Transfer', 'Paid', 'Weekly essentials'],
    ['2026-08-05', 'Utilities & Bills', 'K-Electric electricity bill', 24800, 'Online Banking', 'Paid', 'Monthly electricity'],
    ['2026-08-10', 'Fuel & Transport', 'Car fuel tank refill', 12000, 'Credit Card', 'Paid', 'Full tank petrol'],
    ['2026-08-15', 'Tech & Subscriptions', 'Vercel / OpenAI API sub', 8500, 'Credit Card', 'Paid', 'SaaS tools'],
    ['2026-08-20', 'Dining Out & Personal', 'Dinner with clients', 9200, 'Cash', 'Paid', 'Business meeting'],
    ['TOTAL EXPENSES', '', '', '=SUM(D2:D6)', '', '', 'Auto Total']
]

inc_values = [
    ['Date', 'Source / Client Name', 'Income Category', 'Amount (PKR)', 'Payment Method', 'Notes'],
    ['2026-08-01', 'Full-Stack Retainer', 'Monthly Client Retainer', 350000, 'Bank Transfer', 'Fixed monthly retainer'],
    ['2026-08-12', 'Upwork Project', 'AI Agent Development', 185000, 'Payoneer', 'Project milestone'],
    ['2026-08-22', 'Web Consultation', 'Architecture Audit', 75000, 'Direct Deposit', 'One-time consultation'],
    ['TOTAL INCOME', '', '', '=SUM(D2:D4)', '', 'Auto Total']
]

udhaar_values = [
    ['Date', 'Person Name', 'Transaction Type', 'Amount (PKR)', 'Due Date', 'Status', 'Notes'],
    ['2026-08-03', 'Ali Ahmed', 'Udhaar Given (Lent)', 25000, '2026-09-01', 'Pending', 'Lent for emergency'],
    ['2026-08-14', 'Tech Vendor', 'Udhaar Taken (Borrowed)', 15000, '2026-08-30', 'Pending', 'Hardware purchase due'],
    ['TOTAL UDHAAR OUTSTANDING', '', '', '=SUM(D2:D3)', '', '', 'Auto Total']
]

data_updates = [
    {'range': "'Dashboard'!A1", 'values': dash_values},
    {'range': "'Expenses Log'!A1", 'values': exp_values},
    {'range': "'Income Log'!A1", 'values': inc_values},
    {'range': "'Udhaar & Loans Tracker'!A1", 'values': udhaar_values}
]

sheets.spreadsheets().values().batchUpdate(
    spreadsheetId=sp_id,
    body={'valueInputOption': 'USER_ENTERED', 'data': data_updates}
).execute()

# Make Public Write Link
perm = drive.permissions().create(fileId=sp_id, body={'type': 'anyone', 'role': 'writer'}).execute()
link = f"https://docs.google.com/spreadsheets/d/{sp_id}/edit?usp=sharing"
print("SUCCESS! DIRECT EDITABLE LINK:", link)
