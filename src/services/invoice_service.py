import os
import subprocess
import datetime
from googleapiclient.http import MediaFileUpload
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from src.services.workspace_service import create_google_doc, create_styled_spreadsheet, update_spreadsheet_data, make_file_shareable
from src.services.gmail_service import send_gmail_message

from src.services.time_utils import get_pkt_now

def generate_invoice_number() -> str:
    """Generates a clean timestamped invoice ID like INV-20260826-101"""
    now = get_pkt_now()
    return f"INV-{now.strftime('%Y%m%d')}-{now.strftime('%H%M')}"

def generate_latex_invoice_source(invoice_num: str, client_name: str, client_email: str, amount_str: str, description: str, issue_date: str, due_date: str) -> str:
    """
    Generates pristine LaTeX source code for the invoice with logo.
    """
    c_email = client_email if client_email else 'Client Contact'
    return f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{utf8}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{xcolor}}
\\usepackage{{titlesec}}
\\usepackage{{booktabs}}
\\usepackage{{array}}
\\usepackage{{helvet}}
\\usepackage{{graphicx}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}

\\definecolor{{navy}}{{RGB}}{{16, 44, 87}}
\\definecolor{{accent}}{{RGB}}{{53, 162, 159}}
\\definecolor{{lightgray}}{{RGB}}{{245, 247, 250}}

\\pagestyle{{empty}}

\\begin{{document}}

\\begin{{minipage}}{{0.5\\textwidth}}
    \\includegraphics[width=1.8cm]{{assets/logo.png}} \\\\[6pt]
    {{\\Huge \\bfseries \\color{{navy}} INVOICE}} \\\\[4pt]
    {{\\color{{gray}} \\#{invoice_num}}}
\\end{{minipage}}
\\begin{{minipage}}{{0.5\\textwidth}}
    \\begin{{flushright}}
        {{\\Large \\bfseries Muhammad Hamza}} \\\\[2pt]
        Full-Stack \\& AI Solutions Engineer \\\\
        misterhamza117@gmail.com \\\\
        Islamabad, Pakistan
    \\end{{flushright}}
\\end{{minipage}}

\\vspace{{1.5em}}
\\hrule height 1.5pt
\\vspace{{1.5em}}

\\begin{{minipage}}{{0.5\\textwidth}}
    {{\\bfseries \\color{{navy}} BILLED TO:}} \\\\[4pt]
    {{\\Large \\bfseries {client_name}}} \\\\[2pt]
    {c_email}
\\end{{minipage}}
\\begin{{minipage}}{{0.5\\textwidth}}
    \\begin{{flushright}}
        \\begin{{tabular}}{{ll}}
            \\textbf{{Issue Date:}} & {issue_date} \\\\
            \\textbf{{Due Date:}} & {due_date} \\\\
            \\textbf{{Payment Status:}} & UNPAID
        \\end{{tabular}}
    \\end{{flushright}}
\\end{{minipage}}

\\vspace{{2em}}

\\begin{{tabular}}{{p{{10cm}}r}}
    \\hline
    \\textbf{{DESCRIPTION}} & \\textbf{{AMOUNT}} \\\\
    \\hline
    {description} & \\textbf{{{amount_str}}} \\\\[1em]
    \\hline
\\end{{tabular}}

\\vspace{{1.5em}}

\\begin{{flushright}}
    {{\\Large \\textbf{{Total Amount Due:}} \\quad \\textbf{{{amount_str}}}}}
\\end{{flushright}}

\\vspace{{3em}}

\\textbf{{PAYMENT INSTRUCTIONS}} \\\\[4pt]
• Accepted Methods: Bank Wire Transfer, Payoneer, Wise. \\\\
• Email receipt confirmation to \\textbf{{misterhamza117@gmail.com}} after transfer.

\\vfill
\\begin{{center}}
    {{\\color{{gray}} Thank you for your business!}}
\\end{{center}}

\\end{{document}}
"""

def generate_reportlab_pdf_invoice(pdf_path: str, invoice_num: str, client_name: str, client_email: str, amount_str: str, description: str, issue_date: str, due_date: str):
    """
    Compiles a high-precision, beautifully styled PDF invoice using ReportLab with official MH logo.
    """
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle("InvTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=colors.HexColor("#102C57"))
    inv_num_style = ParagraphStyle("InvNum", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=14, textColor=colors.HexColor("#666666"))
    sender_style = ParagraphStyle("Sender", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, alignment=2)
    heading_style = ParagraphStyle("SectionHead", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=colors.HexColor("#102C57"))
    body_style = ParagraphStyle("BodyText", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14)
    total_style = ParagraphStyle("TotalText", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=2, textColor=colors.HexColor("#102C57"))

    # Logo element
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    logo_path = os.path.join(base_dir, "assets", "logo.png")
    
    if os.path.exists(logo_path):
        logo_img = RLImage(logo_path, width=48, height=48)
        left_cell = Table([[logo_img, Paragraph("<b>INVOICE</b>", title_style)]], colWidths=[55, 215])
        left_cell.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
    else:
        left_cell = Paragraph("<b>INVOICE</b>", title_style)

    header_data = [
        [left_cell, Paragraph("<b>Muhammad Hamza</b><br/>Full-Stack & AI Solutions Engineer<br/>misterhamza117@gmail.com", sender_style)],
        [Paragraph(f"<b>Invoice #:</b> {invoice_num}", inv_num_style), Paragraph("", body_style)]
    ]
    header_table = Table(header_data, colWidths=[270, 270])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#102C57"), spaceBefore=5, spaceAfter=15))

    billing_data = [
        [
            Paragraph(f"<b>BILLED TO:</b><br/><font size=12><b>{client_name}</b></font><br/>{client_email if client_email else 'Client Contact'}", body_style),
            Paragraph(f"<b>Issue Date:</b> {issue_date}<br/><b>Due Date:</b> {due_date}<br/><b>Status:</b> <font color='#D97706'><b>UNPAID</b></font>", body_style)
        ]
    ]
    bill_table = Table(billing_data, colWidths=[270, 270])
    bill_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(bill_table)
    story.append(Spacer(1, 20))

    table_data = [
        [Paragraph("<b>DESCRIPTION</b>", ParagraphStyle("TH", parent=body_style, textColor=colors.white, fontName="Helvetica-Bold")),
         Paragraph("<b>AMOUNT</b>", ParagraphStyle("TH2", parent=body_style, textColor=colors.white, fontName="Helvetica-Bold", alignment=2))],
        [Paragraph(description, body_style), Paragraph(f"<b>{amount_str}</b>", ParagraphStyle("TD2", parent=body_style, alignment=2))]
    ]
    item_table = Table(table_data, colWidths=[400, 140])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#102C57")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#F8FAFC")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(item_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph(f"Total Amount Due: {amount_str}", total_style))
    story.append(Spacer(1, 25))

    payment_box_data = [
        [Paragraph("<b>PAYMENT INSTRUCTIONS</b>", heading_style)],
        [Paragraph("• Accepted Payment Methods: Bank Wire Transfer, Payoneer, or Wise.<br/>• Please send confirmation receipt to <b>misterhamza117@gmail.com</b> once processed.", body_style)]
    ]
    pay_table = Table(payment_box_data, colWidths=[540])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 10)
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 30))
    story.append(Paragraph("<font color='#888888' size=9>Thank you for your business!</font>", ParagraphStyle("Footer", parent=body_style, alignment=1)))

    doc.build(story)

def create_client_invoice(docs_service, sheets_service, drive_service, gmail_service, client_name: str, amount: str, currency: str = "USD", description: str = "Software Development Services", client_email: str = "", send_email: bool = False) -> dict:
    """
    Generates LaTeX .tex source, compiles a professional PDF invoice, uploads PDF to Google Drive,
    logs billing in Google Sheets, and optionally emails the PDF attachment directly to the client.
    """
    invoice_num = generate_invoice_number()
    now = get_pkt_now()
    issue_date = now.strftime("%B %d, %Y")
    due_date = (now + datetime.timedelta(days=14)).strftime("%B %d, %Y")

    clean_amt = str(amount).replace("$", "").replace("USD", "").replace("PKR", "").replace("RS", "").strip()
    if not clean_amt:
        clean_amt = "500"

    curr_symbol = "$" if currency.upper() in ["USD", "$"] else ("PKR " if currency.upper() in ["PKR", "RS"] else f"{currency} ")
    amount_str = f"{curr_symbol}{clean_amt}"

    # 1. Generate & Save LaTeX .tex file
    tex_filename = f"Invoice_{invoice_num}.tex"
    pdf_filename = f"Invoice_{invoice_num}.pdf"
    
    tex_code = generate_latex_invoice_source(invoice_num, client_name, client_email, amount_str, description, issue_date, due_date)
    with open(tex_filename, "w", encoding="utf-8") as f:
        f.write(tex_code)
    print(f"[InvoiceService] Saved LaTeX template to {tex_filename}")

    # 2. Compile to PDF (Try pdflatex first, fallback to ReportLab PDF generator)
    compiled_with_pdflatex = False
    try:
        res = subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(pdf_filename):
            compiled_with_pdflatex = True
            print(f"[InvoiceService] Compiled PDF using pdflatex: {pdf_filename}")
    except Exception as e:
        print(f"[InvoiceService] pdflatex not available, compiling PDF with ReportLab: {e}")

    if not compiled_with_pdflatex:
        generate_reportlab_pdf_invoice(pdf_filename, invoice_num, client_name, client_email, amount_str, description, issue_date, due_date)
        print(f"[InvoiceService] Generated PDF using ReportLab: {pdf_filename}")

    # 3. Upload PDF Invoice to Google Drive
    drive_pdf_url = ""
    drive_file_id = ""
    try:
        if drive_service and os.path.exists(pdf_filename):
            file_metadata = {
                'name': pdf_filename,
                'mimeType': 'application/pdf'
            }
            media = MediaFileUpload(pdf_filename, mimetype='application/pdf')
            uploaded = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            drive_file_id = uploaded.get('id')
            drive_pdf_url = uploaded.get('webViewLink') or f"https://drive.google.com/file/d/{drive_file_id}/view"
            make_file_shareable(drive_service, drive_file_id, make_public=False)
            print(f"[InvoiceService] Uploaded PDF to Drive ID: {drive_file_id}")
    except Exception as e:
        print(f"[InvoiceService] Warning uploading PDF to Drive: {e}")

    # 4. Log in "Client Billing & Invoices" Google Sheet
    sheet_row = [
        invoice_num,
        client_name,
        client_email if client_email else "N/A",
        amount_str,
        description,
        issue_date,
        due_date,
        "UNPAID",
        drive_pdf_url if drive_pdf_url else pdf_filename
    ]

    try:
        search_res = drive_service.files().list(
            q="name = 'Client Billing & Invoices' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
            fields="files(id)"
        ).execute() if drive_service else {}
        
        files = search_res.get("files", [])
        if files:
            spreadsheet_id = files[0]["id"]
            update_spreadsheet_data(sheets_service, spreadsheet_id, "Sheet1!A:I", [sheet_row])
        else:
            headers = ["Invoice #", "Client Name", "Client Email", "Amount", "Description", "Issue Date", "Due Date", "Status", "PDF Link"]
            create_styled_spreadsheet(
                sheets_service,
                drive_service,
                title="Client Billing & Invoices",
                headers=headers,
                rows=[sheet_row],
                theme_color="green"
            )
    except Exception as e:
        print(f"[InvoiceService] Warning logging billing sheet: {e}")

    # 5. Optionally email PDF attachment directly to client
    email_sent = False
    email_msg_id = ""
    if send_email and client_email and gmail_service and os.path.exists(pdf_filename):
        email_subj = f"Invoice {invoice_num} for {description} - Muhammad Hamza"
        email_body = f"""Hi {client_name},

Please find attached invoice {invoice_num} for {description}.

Invoice Amount: {amount_str}
Payment Due Date: {due_date}

Thank you for your business!

Best regards,
Muhammad Hamza
Full-Stack & AI Solutions Engineer
misterhamza117@gmail.com
"""
        try:
            email_msg_id = send_gmail_message(gmail_service, to_email=client_email, subject=email_subj, body_text=email_body, attachment_path=pdf_filename)
            email_sent = True
            print(f"[InvoiceService] Emailed PDF invoice to {client_email}, Message ID: {email_msg_id}")
        except Exception as e:
            print(f"[InvoiceService] Error emailing invoice to {client_email}: {e}")

    return {
        "success": True,
        "invoice_number": invoice_num,
        "client_name": client_name,
        "client_email": client_email,
        "amount": amount_str,
        "due_date": due_date,
        "pdf_filename": pdf_filename,
        "tex_filename": tex_filename,
        "drive_pdf_url": drive_pdf_url,
        "email_sent": email_sent,
        "email_msg_id": email_msg_id
    }
