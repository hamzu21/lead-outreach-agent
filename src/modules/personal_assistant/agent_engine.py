import os
import glob
import json
import datetime
from src.services.time_utils import get_pkt_now, get_pkt_now_str
from src.services.ai_generator import get_ai_client, generate_ai_content
from src.services.memory_db import save_message, get_recent_history
from src.modules.personal_assistant.personal_assistant import PersonalAssistantService
from src.modules.job_agent.job_pipeline import run_job_agent

from src.services.user_profile_service import get_or_create_user_profile, register_guest_introduction, update_user_profile

SYSTEM_INSTRUCTION = """
You are Zeyra, a sharp, brilliant, warm, and highly efficient AI Chief of Staff and Partner for Muhammad Hamza.

STRICT DIRECTNESS & TO-THE-POINT RESPONSE RULES:
- BE DIRECT, TO-THE-POINT, AND CONCISE: Give the EXACT answer, number, or result IMMEDIATELY in your very first sentence!
- NO FILLER INTROS: NEVER output filler chatter like "Abhi check karti hoon...", "Let me search the web right away!", "Chalo test karke dekhte hain!", or "Running diagnostics...".
- NO FAKE AI DISCLAIMERS OR EXCUSES: NEVER make up excuses like "due to security reasons", "cannot share exact figures in public chat", "visit customer portal", or "talk to support". This is Hamza's private personal assistant chat!
- Speak naturally in clean Roman Urdu/English without artificial fluff or repetition.
- MULTI-USER & GUESTS: Greet guests warmly by name when introduced, but remain sharp, helpful, and direct.

CRITICAL TEXT FORMATTING RULES (STRICTLY ENFORCED):
- NEVER output double asterisks `**`, raw headers `###`, or horizontal lines `---`.
- For bold text or section titles, use SINGLE asterisks: `*Title*`.
- For lists, use clean bullet characters: `• item` instead of `* item` or `- item`.
- Ensure output is clean, elegant, and free of messy markdown signs.

Available Capabilities & Automated Actions:
If the user's message indicates an explicit intent to execute one of the following tools, format your internal action plan:
1. MORNING_BRIEF: User wants agenda, morning update, schedule, or daily overview.
2. EXPENSE_LOG: User mentions spending money, buying something, or paying a bill (e.g. "I spent $40 on gas", "Paid 2500 PKR for food").
3. INBOX_DIGEST: User wants to check incoming emails, unread messages, or inbox updates.
4. DRAFTS_DIGEST: User asks to check saved email drafts, draft folder, pending drafts, or draft messages (e.g., "check drafts", "any emails in drafts").
5. SEND_DRAFT: User asks to send a specific email draft.
6. SEND_EMAIL: User asks to send a general email or message (NOT an invoice, receipt, or bill).
7. REPLY_EMAIL: User asks to reply to an email, brand name, person, or previous email (e.g., "duolingo ko reply send kro", "reply to zeusmr777@gmail.com", "reply to linkedin", "reply to last email").
8. JOB_AGENT: User asks to run job application agent or apply for jobs.
9. CREATE_DOC: User asks to create, draft, write, or generate a Google Doc, document, report, or proposal (e.g. "make a doc for project X", "create a google document about AI").
10. CREATE_SHEET: User asks to create, design, or generate a Google Sheet, spreadsheet, Excel table, budget, or log (e.g. "create a google sheet for monthly expenses", "make a spreadsheet of project timeline").
11. MANAGE_WORKSPACE_FILE: User asks to delete, trash, edit, or update a Google Doc or Google Sheet file (e.g. "delete the budget sheet", "personal budget sheet ko delete krdo", "move doc X to trash").
12. LIST_WORKSPACE_FILES: User asks to list, view, show, or browse Google Drive files, spreadsheets, or docs (e.g. "cloud mein kon kon c spreadsheets pri hain sbki list bna k do", "list my spreadsheets", "show my google docs").
13. CREATE_INVOICE: User asks to generate, create, or email/send an invoice, bill, or receipt (e.g. "Client Alex ko $700 ka invoice bana kar bhejo", "invoice client ko bhejo", "send invoice to alex@example.com", "invoice email karo"). CRITICAL RULE: ANY message mentioning 'invoice', 'receipt', 'bill', or sending an invoice MUST ALWAYS be classified as CREATE_INVOICE!
14. AUDIT_WEBSITE: User asks to scan, audit, or analyze a website URL and generate a sales pitch (e.g. "https://example.com ki website audit karo aur pitch doc banao", "audit website acme.com").
15. TECH_RADAR: User asks to view daily tech trends, tech radar, or micro-SaaS ideas (e.g. "show tech radar", "aaj ke micro-saas ideas dekho", "what are top trending client tech stacks").
16. SET_REMINDER: User asks to set, schedule, or create a reminder, alarm, or task alert for a specific date or time (e.g. "flaani date ko mjhe yaad dilana", "28 August ko 3 PM par bill pay karne ka reminder lagao", "remind me in 2 hours to call client").
17. LIST_REMINDERS: User asks to view, check, or list active pending reminders (e.g. "show my reminders", "mere kon kon se reminders scheduled hain").
18. SAVE_MIND_VAULT: User asks to remember, save, store, or record a personal note, password, vehicle maintenance, warranty, or fact in their second brain / mind vault (e.g. "gari ka oil 45000km par change karwaya tha", "wifi password XYZ hai", "laptop serial number ABC-123 remember rakho").
19. CREATE_SLIDES: User asks to create, generate, or make Google Slides, lecture slides, presentation, PPTX, or slide deck for students/classes (e.g. "make lecture slides for React Hooks", "generate Google Slides from this doc", "is text/pdf se slides bana do", "create presentation on Machine Learning").
20. CLEAR_SHEET_DATA: User asks to clear, reset, or remove mock/sample data rows from an existing Google Sheet, or update starting bank balance (e.g. "is sheet mein jo tumne mock data daala woh saara khtm kro", "tmne poorana data remove ni kia", "purana data delete kardo", "bank balance 14100 daalo", "clear sample rows from spreadsheet").
"""

class ConversationalAgent:
    def __init__(self):
        self.pa_service = PersonalAssistantService()

    def process_message(self, chat_id: str, user_text: str) -> str:
        """
        Processes a natural language message from the user, retrieves recent chat memory,
        evaluates tool intent or conversational reply, and saves state to SQLite memory.
        """
        # 1. Load user profile context
        user_profile = get_or_create_user_profile(chat_id)
        user_name = user_profile.get("name", "Friend")
        user_rel = user_profile.get("relationship", "Guest")
        user_notes = user_profile.get("notes", "")

        # 2. Load recent conversation history from SQLite (up to 16 messages / 8 turns)
        recent_history = get_recent_history(chat_id=chat_id, limit=16)

        # Current timestamp for relative date calculation by Gemini in Pakistan Standard Time (PKT, UTC+5)
        current_time_str = get_pkt_now_str("%Y-%m-%d %H:%M:%S")

        # Build context prompt
        history_formatted = ""
        if recent_history:
            history_formatted = "\nConversation History (Recent Messages):\n"
            for msg in recent_history:
                role_label = user_name if msg["role"] == "user" else "Zeyra"
                history_formatted += f"{role_label}: {msg['content']}\n"
        # Fast Conversational Route for simple greetings & casual chat (< 1.5s latency)
        lower_txt = user_text.lower().strip()
        action_keywords = ["sheet", "doc", "email", "slide", "expense", "invoice", "search", "audit", "clear", "balance", "remind", "draft", "brief", "radar", "vault", "pdf", "book", "chapter", "topic"]
        is_action_request = any(kw in lower_txt for kw in action_keywords)
        
        if not is_action_request and len(user_text.split()) <= 12:
            try:
                chat_prompt = f"{SYSTEM_INSTRUCTION}\nActive Speaker: {user_name}\n{history_formatted}\nUser: {user_text}\nZeyra:"
                conv_reply = generate_ai_content(chat_prompt)
                save_message(chat_id, "user", user_text)
                save_message(chat_id, "assistant", conv_reply)
                return conv_reply
            except Exception as ce:
                print(f"[ConversationalAgent] Fast route exception: {ce}")

        intent_prompt = f"""
{SYSTEM_INSTRUCTION}

Active Speaker Profile:
• Name: {user_name}
• Relationship: {user_rel}
• Stored Personal Notes: {user_notes if user_notes else 'None recorded yet'}

Current Local Time (Pakistan Standard Time PKT, UTC+5 / Asia/Karachi): {current_time_str}

{history_formatted}
{user_name}'s Latest Message: "{user_text}"

CRITICAL RULE FOR EMAIL DELETION & CHECKING:
1. If user asks to delete, trash, or remove emails (e.g. 'duolingo ki delete krdo', 'delete krdo', 'hata do'), set "intent": "TRASH_EMAIL" and extract keyword in "to_email".
2. If user asks to check, verify, or count remaining emails (e.g. 'or bhi hain bayt ki emails?', 'check kro emails hain ya nahi', 'kitni emails baqi hain'), set "intent": "CHECK_EMAILS" and extract keyword (e.g. 'bayt', 'duolingo') in "to_email".
3. If user provides a university faculty URL (e.g. 'https://www.kaust.edu.sa/en/study/faculty') and asks to extract/find professors in AI, Cyber Security, or CS, set "intent": "SCRAPE_FACULTY" and extract URL in "audit_url".

Return JSON with format:
{{
  "intent": "MORNING_BRIEF" | "EXPENSE_LOG" | "INBOX_DIGEST" | "DRAFTS_DIGEST" | "SEND_DRAFT" | "SEND_EMAIL" | "REPLY_EMAIL" | "TRASH_EMAIL" | "CHECK_EMAILS" | "JOB_AGENT" | "ACADEMIC_OUTREACH" | "SCRAPE_FACULTY" | "CREATE_DOC" | "CREATE_SHEET" | "MANAGE_WORKSPACE_FILE" | "LIST_WORKSPACE_FILES" | "CREATE_INVOICE" | "AUDIT_WEBSITE" | "TECH_RADAR" | "SET_REMINDER" | "LIST_REMINDERS" | "CREATE_SLIDES" | "CLEAR_SHEET_DATA" | "GENERAL_CONVERSATION",
  "expense_details": "Extracted expense text if intent is EXPENSE_LOG, else empty string",
  "parsed_expense": {{
    "amount": 500.0,
    "vendor": "Store or payee name",
    "category": "Personal & Misc",
    "currency": "PKR",
    "description": "Short note"
  }},
  "draft_id": "Extracted draft ID if intent is SEND_DRAFT, else empty string",
  "to_email": "Extracted recipient email address, brand name, or sender keyword (e.g. 'duolingo', 'bayt', 'zeusmr777@gmail.com', 'linkedin') if intent is SEND_EMAIL, REPLY_EMAIL, TRASH_EMAIL, or CHECK_EMAILS, else empty string",
  "email_subject": "Professional email subject line if intent is SEND_EMAIL or REPLY_EMAIL, else empty string",
  "email_body": "Well-formatted professional email body text if intent is SEND_EMAIL, else empty string",
  "reply_instructions": "Extracted user reply instructions if intent is REPLY_EMAIL, else empty string",
  "doc_title": "Extracted document or spreadsheet title if intent is CREATE_DOC, CREATE_SHEET, MANAGE_WORKSPACE_FILE, or CLEAR_SHEET_DATA, else empty string",
  "doc_instructions": "Extracted instructions or content details if intent is CREATE_DOC, CREATE_SHEET, or SCRAPE_FACULTY (e.g. 'AI, Cyber Security'), else empty string",
  "starting_balance": "Extracted numerical starting bank balance if user specifies starting balance (e.g. 14100), else empty string",
  "client_name": "Extracted client name if intent is CREATE_INVOICE, else empty string",
  "invoice_amount": "Extracted numerical amount if intent is CREATE_INVOICE, else empty string",
  "invoice_currency": "Extracted currency code like USD or PKR if intent is CREATE_INVOICE, default USD",
  "invoice_desc": "Extracted work description if intent is CREATE_INVOICE, default 'Software Development Services'",
  "send_invoice_email": true if user asks to email or send the invoice to client email, else false,
  "audit_url": "Extracted website or faculty URL if intent is AUDIT_WEBSITE or SCRAPE_FACULTY, else empty string",
  "reminder_text": "Extracted task description if intent is SET_REMINDER, else empty string",
  "remind_at_datetime": "Calculated target date and time in format 'YYYY-MM-DD HH:MM:SS' based on user's instruction and Current Local Server Time if intent is SET_REMINDER, else empty string",
  "response": "Your direct, conversational response to the user. If an action tool will be executed, write a brief friendly intro."
}}
"""
        try:
            raw_res = generate_ai_content(intent_prompt, response_mime_type="application/json")
            
            # Clean markdown code blocks if wrapped by Gemini
            clean_json_str = raw_res.strip()
            if clean_json_str.startswith("```json"):
                clean_json_str = clean_json_str[7:]
            if clean_json_str.startswith("```"):
                clean_json_str = clean_json_str[3:]
            if clean_json_str.endswith("```"):
                clean_json_str = clean_json_str[:-3]
            clean_json_str = clean_json_str.strip()

            res_data = json.loads(clean_json_str)
            intent = res_data.get("intent", "GENERAL_CONVERSATION")
            base_response = res_data.get("response", "")
            expense_text = res_data.get("expense_details", user_text)
            draft_id_val = res_data.get("draft_id", "").strip()
            to_email_val = res_data.get("to_email", "").strip()
            email_subj_val = res_data.get("email_subject", "Meeting Request").strip()
            email_body_val = res_data.get("email_body", user_text).strip()
            reply_inst_val = res_data.get("reply_instructions", user_text).strip()
            doc_title_val = res_data.get("doc_title", "Untitled Workspace File").strip()
            doc_inst_val = res_data.get("doc_instructions", user_text).strip()
            client_name_val = res_data.get("client_name", "Valued Client").strip()
            invoice_amt_val = res_data.get("invoice_amount", "500").strip()
            invoice_curr_val = res_data.get("invoice_currency", "USD").strip()
            invoice_desc_val = res_data.get("invoice_desc", "Software Development Services").strip()
            starting_balance_val = res_data.get("starting_balance", "").strip()
            audit_url_val = res_data.get("audit_url", "").strip()
            reminder_text_val = res_data.get("reminder_text", "").strip()
            remind_at_val = res_data.get("remind_at_datetime", "").strip()

            final_reply = base_response

            # 1.4 Safety Net Override for Email Deletion vs Email Check vs Faculty Scraping Intent
            del_words = ["delete", "trash", "hata", "remove", "khatam"]
            check_words = ["check", "dekh", "kitni", "or bhi", "aur bhi", "baqi", "remains", "bhi hain", "kya hain"]
            mail_words = ["email", "emails", "mail", "inbox", "duolingo", "freelancer", "alibaba", "linkedin", "bayt"]
            lower_u = user_text.lower()

            if "http" in lower_u and any(w in lower_u for w in ["faculty", "professor", "professors", "kaust", "data nikaal", "data nikal", "list", "extract"]):
                print(f"[ConversationalAgent] Safety Override: Forcing SCRAPE_FACULTY intent for: {user_text}")
                intent = "SCRAPE_FACULTY"
            elif any(m in lower_u for m in mail_words):
                if any(c in lower_u for c in check_words) and not any(d in lower_u for d in ["delete kr", "saari delete", "trash kr"]):
                    print(f"[ConversationalAgent] Safety Override: Forcing CHECK_EMAILS intent for: {user_text}")
                    intent = "CHECK_EMAILS"
                elif any(w in lower_u for w in del_words):
                    if intent != "TRASH_EMAIL":
                        print(f"[ConversationalAgent] Safety Override: Forcing TRASH_EMAIL intent for: {user_text}")
                        intent = "TRASH_EMAIL"

            # 1.5 Send instant preliminary status update for time-taking tasks to eliminate user waiting perception
            status_messages = {
                "SCRAPE_FACULTY": "🎓 *Ji Hamza, main university website scan karke professors ka data extract aur Google Sheet generate kar rahi hoon...* ⏳",
                "ACADEMIC_OUTREACH": "🎓 *Ji Hamza, main Academic Professor Outreach campaign start kar rahi hoon (Semantic Scholar paper research + CV attachment)...* ⏳",
                "CHECK_EMAILS": "🔍 *Ji Hamza, main live Gmail scan karke count verify kar rahi hoon...* ⏳",
                "TRASH_EMAIL": "🗑️ *Ji Hamza, main email trash/delete kar rahi hoon...* ⏳",
                "WEB_SEARCH": "🔍 *Ji Hamza, main live web search karke info gather kar rahi hoon...* ⏳",
                "CREATE_SLIDES": "📊 *Ji Hamza, main presentation slides design aur generate kar rahi hoon...* ⏳",
                "CREATE_SHEET": "📑 *Ji Hamza, main Google Spreadsheet generate kar rahi hoon...* ⏳",
                "CLEAR_SHEET_DATA": "🧹 *Ji Hamza, main sheet ka data clear aur balance update kar rahi hoon...* ⏳",
                "AUDIT_WEBSITE": "🔍 *Ji Hamza, main website scan karke audit report compile kar rahi hoon...* ⏳",
                "CREATE_DOC": "📄 *Ji Hamza, main Google Document generate kar rahi hoon...* ⏳",
                "TEACHING_STUDIO": "🎓 *Ji Hamza, main teaching package document tayyar kar rahi hoon...* ⏳",
                "CREATE_INVOICE": "🧾 *Ji Hamza, main client invoice PDF compile kar rahi hoon...* ⏳",
                "INBOX_DIGEST": "📥 *Ji Hamza, main aap ka Gmail inbox scan kar rahi hoon...* ⏳",
                "MORNING_BRIEF": "🌅 *Ji Hamza, main aap ki Morning Briefing compile kar rahi hoon...* ⏳"
            }

            if intent in status_messages and chat_id:
                try:
                    from src.services.telegram_service import send_telegram_message
                    send_telegram_message(status_messages[intent], chat_id=chat_id)
                except Exception as se:
                    print(f"[ConversationalAgent] Notice sending preliminary status: {se}")

            # 2. Execute Action Tools based on intent
            if intent == "MORNING_BRIEF":
                brief_content = self.pa_service.get_morning_briefing()
                final_reply = f"{base_response}\n\n{brief_content}"

            elif intent == "CHECK_EMAILS":
                target_kw = to_email_val or user_text
                import re
                clean_kw = re.sub(r"(?i)\b(or|aur|bhi|hain|check|kro|karo|emails|email|delete|hui|ya|nahi|baqi)\b", "", target_kw).strip(" ?.,!")
                clean_kw = clean_kw or target_kw
                res = self.pa_service.check_email_count(clean_kw)
                if res.get("success"):
                    active_cnt = res.get("active_count", 0)
                    trash_cnt = res.get("trash_count", 0)
                    if active_cnt > 0:
                        final_reply = (
                            f"🔍 *Live Gmail Check Result for `{clean_kw}`*:\n\n"
                            f"• 📥 *Active Inbox Emails*: `{active_cnt}`\n"
                            f"• 🗑️ *Emails in Trash*: `{trash_cnt}`\n\n"
                            f"💡 *Hamza, active inbox me abhi bhi {active_cnt} emails baqi hain!* Kya main inhein bhi trash kar doon?"
                        )
                    else:
                        final_reply = (
                            f"✅ *Live Gmail Verification Complete for `{clean_kw}`*:\n\n"
                            f"• 📥 *Active Inbox Emails*: `0` (100% Cleared!)\n"
                            f"• 🗑️ *Emails in Trash*: `{trash_cnt}`\n\n"
                            f"🎉 *`{clean_kw}` ki tamam emails trash me move ho chuki hain! Inbox me 0 emails baqi hain.*"
                        )
                else:
                    final_reply = f"⚠️ Could not verify email count: {res.get('error')}"

            elif intent == "TRASH_EMAIL":
                target_kw = to_email_val or user_text
                res = self.pa_service.trash_email(target_kw)
                if res.get("success"):
                    count_val = res.get("count", 1)
                    rem_val = res.get("remaining", 0)
                    rem_str = f"• 📥 *Remaining Active Emails*: `{rem_val}`\n" if rem_val > 0 else "• 📥 *Remaining Active Emails*: `0` (All Cleared!)\n"
                    final_reply = (
                        f"🗑️ *Emails Moved to Trash Successfully!*\n\n"
                        f"• *Target/Keyword*: `{target_kw}`\n"
                        f"• *Emails Trashed*: `{count_val} matching email(s)`\n"
                        f"{rem_str}"
                        f"• *Sample Message ID*: `{res.get('msg_id')}`\n\n"
                        f"_(The matching emails have been moved to your Gmail Trash bin.)_"
                    )
                else:
                    final_reply = f"⚠️ Could not delete email: {res.get('error')}"

            elif intent == "EXPENSE_LOG":
                combined_exp_text = f"{user_text} {expense_text}"
                parsed_exp_obj = res_data.get("parsed_expense")
                target_kw = doc_title_val.strip() if doc_title_val and doc_title_val != "Untitled Workspace File" else None
                exp_data = self.pa_service.process_expense(combined_exp_text, parsed_data=parsed_exp_obj, target_spreadsheet_id=target_kw)
                
                if exp_data.get("logged_to_sheet", True):
                    target_sheet_id = exp_data.get("target_spreadsheet_id") or exp_data.get("spreadsheet_id")
                    target_tab = exp_data.get("target_tab", "Expenses")
                    target_url = f"https://docs.google.com/spreadsheets/d/{target_sheet_id}/edit?usp=sharing" if target_sheet_id else ""
                    link_str = f"\n\n🔗 [Open & View Target Google Sheet]({target_url})" if target_url else ""
                    final_reply = (
                        f"🧾 *Expense Logged Successfully!*\n\n"
                        f"• *Vendor/Item*: {exp_data.get('vendor')}\n"
                        f"• *Amount*: {exp_data.get('currency')} {exp_data.get('amount')}\n"
                        f"• *Category*: {exp_data.get('category')}\n"
                        f"• *Date*: {exp_data.get('date')}\n"
                        f"• *Logged To Tab*: `{target_tab}`\n"
                        f"• *Details*: {exp_data.get('description')}"
                        f"{link_str}"
                    )
                else:
                    final_reply = f"⚠️ Could not log entry to Google Sheet: {exp_data.get('error', 'Google API failure')}. Please retry."

            elif intent == "INBOX_DIGEST":
                digest_content = self.pa_service.get_inbox_digest()
                final_reply = f"{base_response}\n\n{digest_content}"

            elif intent == "DRAFTS_DIGEST":
                drafts_content = self.pa_service.get_drafts_digest()
                final_reply = f"{base_response}\n\n{drafts_content}"

            elif intent == "SEND_DRAFT":
                if draft_id_val:
                    success = self.pa_service.send_draft(draft_id_val)
                    if success:
                        final_reply = f"✅ Sent email draft `{draft_id_val}` successfully!"
                    else:
                        final_reply = f"⚠️ Could not find or send draft `{draft_id_val}`."
                else:
                    final_reply = self.pa_service.get_drafts_digest()

            elif intent == "SEND_EMAIL":
                target_kw = to_email_val or user_text
                resolved = self.pa_service.resolve_target_email(target_kw)
                target_email = resolved.get("to_email", "")
                target_subj = email_subj_val or resolved.get("subject", "Meeting Request")

                # Check if email is an invoice email requiring PDF attachment
                attachment_file = None
                if any(kw in (user_text + email_body_val + target_subj).lower() for kw in ["invoice", "receipt", "bill", "attached"]):
                    pdf_files = sorted(glob.glob("Invoice_INV-*.pdf"), key=os.path.getmtime, reverse=True)
                    if pdf_files:
                        attachment_file = pdf_files[0]
                        print(f"[ConversationalAgent] Found invoice attachment for SEND_EMAIL: {attachment_file}")

                if target_email and "@" in target_email:
                    res = self.pa_service.send_email(
                        to_email=target_email,
                        subject=target_subj,
                        body_text=email_body_val,
                        attachment_path=attachment_file
                    )
                    if res.get("success"):
                        attach_str = f"\n• 📎 *Attached File*: `{os.path.basename(attachment_file)}`" if attachment_file else ""
                        final_reply = (
                            f"📧 *Email Sent Successfully!*{attach_str}\n\n"
                            f"• *To*: `{target_email}`\n"
                            f"• *Subject*: {target_subj}\n"
                            f"• *Message ID*: `{res.get('msg_id')}`"
                        )
                    else:
                        final_reply = f"⚠️ Failed to send email to `{target_email}`: {res.get('error')}"
                else:
                    final_reply = "⚠️ Please specify a valid recipient email address to send an email."

            elif intent == "REPLY_EMAIL":
                target_kw = to_email_val or user_text
                resolved = self.pa_service.resolve_target_email(target_kw)
                target_email = resolved.get("to_email", "")
                target_subj = resolved.get("subject") or email_subj_val or "Inquiry"

                if target_email and "@" in target_email:
                    res = self.pa_service.reply_to_email(
                        to_email=target_email,
                        subject=target_subj,
                        instructions=reply_inst_val
                    )
                    if res.get("success"):
                        final_reply = (
                            f"💬 *AI Email Reply Sent Successfully!*\n\n"
                            f"• *To*: `{target_email}`\n"
                            f"• *Subject*: {res.get('subject')}\n"
                            f"• *Message ID*: `{res.get('msg_id')}`\n\n"
                            f"*Generated Reply Body*:\n_{res.get('generated_body')}_"
                        )
                    else:
                        final_reply = f"⚠️ Failed to send reply to `{target_email}`: {res.get('error')}"
                else:
                    final_reply = "⚠️ Could not automatically resolve target recipient email address."

            elif intent == "CREATE_DOC":
                res = self.pa_service.create_google_document(
                    title=doc_title_val,
                    instructions=doc_inst_val
                )
                if res.get("success"):
                    final_reply = (
                        f"📄 *Google Doc Created Successfully!*\n\n"
                        f"• *Title*: {res.get('title')}\n"
                        f"• *Doc ID*: `{res.get('doc_id')}`\n"
                        f"🔗 *Open/Edit Document*: {res.get('url')}"
                    )
                else:
                    final_reply = f"⚠️ Failed to create Google Doc: {res.get('error')}"

            elif intent == "CREATE_SHEET":
                res = self.pa_service.create_google_sheet(
                    title=doc_title_val,
                    instructions=doc_inst_val
                )
                if res.get("success"):
                    sheet_url = res.get("url")
                    final_reply = (
                        f"📊 *Google Spreadsheet Generated Successfully!* 💸\n\n"
                        f"• *Title*: {res.get('title')}\n"
                        f"• *Structure*: Multi-Tab Financial Dashboard & Logs\n"
                        f"• *Access*: Anyone with link can view/edit\n\n"
                        f"🔗 [Open & Edit Google Spreadsheet]({sheet_url})"
                    )
                else:
                    final_reply = f"⚠️ Failed to create Google Sheet: {res.get('error')}"

            elif intent == "MANAGE_WORKSPACE_FILE":
                res = self.pa_service.trash_workspace_file(doc_title_val)
                if res.get("success"):
                    final_reply = f"🗑️ *Google Workspace File Trashed*: `{res.get('file_name', doc_title_val)}` (ID: `{res.get('file_id')}`)"
                else:
                    final_reply = f"⚠️ Failed to manage/trash file: {res.get('error')}"

            elif intent == "LIST_WORKSPACE_FILES":
                digest_content = self.pa_service.list_workspace_files_digest(file_type="spreadsheet")
                final_reply = f"{base_response}\n\n{digest_content}"

            elif intent == "CREATE_INVOICE":
                res = self.pa_service.create_invoice(
                    client_name=client_name_val,
                    amount=invoice_amt_val,
                    currency=invoice_curr_val,
                    description=invoice_desc_val,
                    client_email=to_email_val,
                    send_email=bool(send_invoice_email_val or (to_email_val and "@" in to_email_val))
                )
                if res.get("success"):
                    email_msg = f"• 📧 *PDF Emailed To Client*: `{res.get('client_email')}` (Msg ID: `{res.get('email_msg_id')}`)\n" if res.get("email_sent") else "• ℹ️ *Email*: PDF ready (not emailed yet).\n"
                    drive_url = f"• 🔗 *Google Drive PDF Link*: {res.get('drive_pdf_url')}\n" if res.get("drive_pdf_url") else ""
                    final_reply = (
                        f"🧾 *LaTeX PDF Invoice Generated Successfully!*\n\n"
                        f"• *Invoice #*: `{res.get('invoice_number')}`\n"
                        f"• *Client*: {res.get('client_name')}\n"
                        f"• *Amount*: {res.get('amount')}\n"
                        f"• *Due Date*: {res.get('due_date')}\n"
                        f"• *LaTeX Source File*: `{res.get('tex_filename')}` (.tex)\n"
                        f"• *Compiled PDF File*: `{res.get('pdf_filename')}` (.pdf)\n"
                        f"{email_msg}"
                        f"{drive_url}"
                        f"• 📊 *Status*: Logged into 'Client Billing & Invoices' sheet."
                    )
                else:
                    final_reply = f"⚠️ Failed to generate invoice: {res.get('error')}"

            elif intent == "AUDIT_WEBSITE":
                target_url = audit_url_val or user_text
                res = self.pa_service.audit_website(target_url)
                if res.get("success"):
                    final_reply = (
                        f"🔍 *Website Audit & Cold Pitch Generated!*\n\n"
                        f"• *Target Domain*: `{res.get('domain')}`\n"
                        f"• *Report Title*: {res.get('doc_title')}\n"
                        f"🔗 *Open Full Audit & Pitch Doc*: {res.get('doc_url')}"
                    )
                else:
                    final_reply = f"⚠️ Website audit failed: {res.get('error')}"

            elif intent == "TECH_RADAR":
                radar_content = self.pa_service.get_tech_radar()
                final_reply = f"{base_response}\n\n{radar_content}"

            elif intent == "JOB_AGENT":
                final_reply = "🛑 *Job Application Agent is currently disabled* as per your request. If you ever want to re-enable it in the future, just let me know!"

            elif intent == "ACADEMIC_OUTREACH":
                res = self.pa_service.run_professor_outreach(limit=10)
                if res.get("success"):
                    cv_name = os.path.basename(res.get('attached_cv', 'Muhammad_Hamza_CV.pdf')) if res.get('attached_cv') else "Muhammad_Hamza_CV.pdf"
                    final_reply = (
                        f"🎓 *Academic Professor Outreach Drafts Created!* 🏛️\n\n"
                        f"• *Gmail Drafts Prepared*: `{res.get('drafts_created')}`\n"
                        f"• *Safety Protocol*: Saved to Gmail Drafts (NOT sent directly)\n"
                        f"• *Research Lookup*: Semantic Scholar & OpenAlex APIs\n"
                        f"• *CV Attached*: `{cv_name}`\n"
                        f"• *Tracker File*: `{res.get('csv_file')}`\n\n"
                        f"💡 *Hamza, aap Gmail drafts me in sabko review kar lein.* Jab aap approve karein to mujhse kahein: *'in drafts ko send/schedule krdo'*!"
                    )
                else:
                    final_reply = f"⚠️ Could not create professor outreach drafts: {res.get('error')}"

            elif intent == "SCRAPE_FACULTY":
                import re
                target_url = audit_url_val
                if not target_url or "http" not in target_url:
                    urls = re.findall(r'https?://[^\s]+', user_text)
                    target_url = urls[0] if urls else ""

                if target_url:
                    res = self.pa_service.extract_professors_from_url(target_url, fields=doc_inst_val or "AI, Cyber Security, Computer Science")
                    if res.get("success"):
                        sheet_url = res.get("url")
                        univ = res.get("university", "University")
                        cnt = res.get("count", 0)
                        link_msg = f"\n\n🔗 [Open & Edit Target Google Sheet]({sheet_url})" if sheet_url else ""
                        final_reply = (
                            f"📑 *Google Spreadsheet Generated for {univ} Professors!* 🎓\n\n"
                            f"• *University*: {univ} ({res.get('country')})\n"
                            f"• *Professors Extracted*: `{cnt}`\n"
                            f"• *Target Fields*: `{res.get('target_fields')}`\n"
                            f"• *Access*: Anyone with link can view/edit"
                            f"{link_msg}\n\n"
                            f"_(Appended to local professors_list.csv for Academic Outreach Agent!)_"
                        )
                    else:
                        final_reply = f"⚠️ Could not extract faculty data: {res.get('error')}"
                else:
                    final_reply = "⚠️ Please provide a valid university faculty page URL (e.g. https://www.kaust.edu.sa/en/study/faculty)."

            elif intent == "SET_REMINDER":
                rem_text = reminder_text_val or user_text
                rem_time = remind_at_val
                if not rem_time:
                    rem_time = (get_pkt_now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
                
                res = self.pa_service.set_reminder(chat_id=chat_id, reminder_text=rem_text, remind_at_str=rem_time)
                if res.get("success"):
                    final_reply = (
                        f"⏰ *Reminder Scheduled Successfully!*\n\n"
                        f"• *Reminder*: {res.get('reminder_text')}\n"
                        f"• *Scheduled Time*: `{res.get('remind_at')}`\n"
                        f"• *ID*: #{res.get('id')}\n\n"
                        f"_(I will send you an automatic alert message in this chat at the exact scheduled time!)_"
                    )
                else:
                    final_reply = f"⚠️ Could not schedule reminder: {res.get('error')}"

            elif intent == "LIST_REMINDERS":
                digest_content = self.pa_service.get_reminders_digest(chat_id)
                final_reply = f"{base_response}\n\n{digest_content}"

            elif intent == "SAVE_MIND_VAULT":
                res = self.pa_service.save_mind_vault_fact(chat_id, user_text)
                if res.get("success"):
                    final_reply = (
                        f"🧠 *Personal Fact Recorded to Mind Vault!*\n\n"
                        f"• *Category*: `{res.get('category')}`\n"
                        f"• *Topic*: {res.get('fact_key')}\n"
                        f"• *Recorded Detail*: {res.get('fact_value')}\n"
                        f"• *ID*: #{res.get('id')}\n\n"
                        f"_(I have stored this in your second brain. Ask me anytime to recall it!)_"
                    )
                else:
                    final_reply = "⚠️ Could not save fact to Mind Vault."

            elif intent == "QUERY_MIND_VAULT":
                answer = self.pa_service.query_mind_vault(chat_id, user_text)
                final_reply = f"🧠 *Mind Vault Recall*:\n\n{answer}"

            elif intent == "FOCUS_OPTIMIZER":
                schedule = self.pa_service.optimize_focus_schedule(user_text)
                final_reply = f"{base_response}\n\n{schedule}"

            elif intent == "TEACHING_STUDIO":
                topic = doc_inst_val or user_text
                res = self.pa_service.create_teaching_package(topic)
                if res.get("success"):
                    final_reply = (
                        f"🎓 *Academic Teaching Package Generated!*\n\n"
                        f"• *Title*: {res.get('title')}\n"
                        f"• *Package Includes*: Lecture Outline, 5 Exercises & Solutions\n"
                        f"🔗 *Open Google Doc*: {res.get('url')}"
                    )
                else:
                    final_reply = f"⚠️ Could not generate teaching package: {res.get('error')}"

            elif intent == "BUDGET_DIRECTOR":
                report = self.pa_service.get_financial_health_report()
                final_reply = f"{base_response}\n\n{report}"

            elif intent == "INTRODUCE_GUEST":
                guest_info = register_guest_introduction(chat_id, user_text)
                g_name = guest_info.get("name", "Guest")
                g_rel = guest_info.get("relationship", "Friend")
                g_notes = guest_info.get("notes", "")
                
                update_user_profile(chat_id, new_note=f"Introduced {g_name} ({g_rel}: {g_notes})")
                
                final_reply = (
                    f"Assalam-o-Alaikum {g_name}! 🌟\n\n"
                    f"Aap se mil kar bohot khushi hui! Main Zeyra hoon, Hamza ki AI partner aur executive assistant. "
                    f"Hamza ne aap ke baare me bataya hai ({g_notes}). "
                    f"Aap jab bhi aayein, mujhse khule dil se baat kar sakte hain!"
                )

            elif intent == "WEB_SEARCH":
                final_reply = self.pa_service.perform_web_search(user_text, history_context=history_formatted)

            elif intent == "CREATE_SLIDES":
                topic = doc_inst_val or user_text
                res = self.pa_service.create_lecture_slides(topic)
                if res.get("success"):
                    slides_url = res.get("url")
                    final_reply = (
                        f"📊 *Google Slides Presentation Generated Successfully!* 🎓\n\n"
                        f"• *Title*: {res.get('title')}\n"
                        f"• *Slide Count*: {res.get('slides_count')} Widescreen Slides\n"
                        f"• *Instructor*: {res.get('outline', {}).get('instructor', 'Muhammad Hamza')}\n"
                        f"• *Theme*: Modern High-Contrast Light Snow (16:9 Widescreen)\n\n"
                        f"🔗 [Open & Edit Google Slides Presentation]({slides_url})"
                    )
            elif intent == "CLEAR_SHEET_DATA":
                target_kw = doc_title_val or user_text
                s_bal = None
                if starting_balance_val:
                    try:
                        s_bal = float(starting_balance_val.replace(",", "").strip())
                    except Exception:
                        s_bal = None

                res = self.pa_service.clear_and_update_sheet(target_kw, starting_balance=s_bal)
                if res.get("success"):
                    sheet_url = res.get("url")
                    bal_msg = f"• *Starting Bank Balance Configured*: PKR {res.get('starting_balance'):,}\n" if res.get("starting_balance") else ""
                    final_reply = (
                        f"🧹 *Google Sheet Data Cleared & Updated!* 💸\n\n"
                        f"• *Target Sheet*: `{res.get('title')}`\n"
                        f"• *Action*: All mock/sample rows cleared from Expenses & Income tabs\n"
                        f"{bal_msg}"
                        f"• *Access*: Clean sheet ready for your real entries\n\n"
                        f"🔗 [Open & Edit Clean Google Sheet]({sheet_url})"
                    )
                else:
                    final_reply = f"⚠️ Could not clear sheet data: {res.get('error')}"

            # 3. Save User Message & Zeyra Response to SQLite Memory
            save_message(chat_id, "user", user_text)
            save_message(chat_id, "assistant", final_reply)

            return final_reply

        except Exception as e:
            print(f"[ConversationalAgent] Exception: {e}")
            # Fallback simple conversational reply
            fallback_prompt = f"{SYSTEM_INSTRUCTION}\n{history_formatted}\nUser: {user_text}\nZeyra:"
            fallback_reply = generate_ai_content(fallback_prompt)
            save_message(chat_id, "user", user_text)
            save_message(chat_id, "assistant", fallback_reply)
            return fallback_reply
