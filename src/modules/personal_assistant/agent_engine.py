import json
from src.services.ai_generator import get_ai_client, generate_ai_content
from src.services.memory_db import save_message, get_recent_history
from src.modules.personal_assistant.personal_assistant import PersonalAssistantService
from src.modules.job_agent.job_pipeline import run_job_agent

SYSTEM_INSTRUCTION = """
You are Zeyra, a brilliant, warm, and highly capable AI Executive Assistant pair-programming and assisting Muhammad Hamza.
You manage his daily workflow, automated job applications, client outreach, expense tracking, email inbox/drafts management, and teaching/lecture productivity.

Your Tone & Persona:
- Professional, intelligent, warm, concise, and proactive.
- Speak naturally like a high-level personal voice assistant.
- Use clean Markdown formatting suitable for Telegram messaging (bold, short bullet points).
- You have persistent memory of past conversation turns.

Available Capabilities & Automated Actions:
If the user's message indicates an explicit intent to execute one of the following tools, format your internal action plan:
1. MORNING_BRIEF: User wants agenda, morning update, schedule, or daily overview.
2. EXPENSE_LOG: User mentions spending money, buying something, or paying a bill (e.g. "I spent $40 on gas", "Paid 2500 PKR for food").
3. INBOX_DIGEST: User wants to check incoming emails, unread messages, or inbox updates.
4. DRAFTS_DIGEST: User asks to check saved email drafts, draft folder, pending drafts, or draft messages (e.g., "check drafts", "any emails in drafts").
5. SEND_DRAFT: User asks to send a specific email draft.
6. SEND_EMAIL: User asks to send an email or message to an email address or contact.
7. REPLY_EMAIL: User asks to reply to an email, brand name, person, or previous email (e.g., "duolingo ko reply send kro", "reply to zeusmr777@gmail.com", "reply to linkedin", "reply to last email").
8. JOB_AGENT: User asks to run job application agent or apply for jobs.
9. CREATE_DOC: User asks to create, draft, write, or generate a Google Doc, document, report, or proposal (e.g. "make a doc for project X", "create a google document about AI").
10. CREATE_SHEET: User asks to create, design, or generate a Google Sheet, spreadsheet, Excel table, budget, or log (e.g. "create a google sheet for monthly expenses", "make a spreadsheet of project timeline").
11. MANAGE_WORKSPACE_FILE: User asks to delete, trash, edit, or update a Google Doc or Google Sheet file (e.g. "delete the budget sheet", "personal budget sheet ko delete krdo", "move doc X to trash").
12. LIST_WORKSPACE_FILES: User asks to list, view, show, or browse Google Drive files, spreadsheets, or docs (e.g. "cloud mein kon kon c spreadsheets pri hain sbki list bna k do", "list my spreadsheets", "show my google docs").
13. GENERAL_CONVERSATION: User is asking a question, chatting, seeking advice, planning, or teaching guidance.
"""

class ConversationalAgent:
    def __init__(self):
        self.pa_service = PersonalAssistantService()

    def process_message(self, chat_id: str, user_text: str) -> str:
        """
        Processes a natural language message from the user, retrieves recent chat memory,
        evaluates tool intent or conversational reply, and saves state to SQLite memory.
        """
        # 1. Load recent conversation history from SQLite
        recent_history = get_recent_history(chat_id=chat_id, limit=8)

        # Build context prompt
        history_formatted = ""
        if recent_history:
            history_formatted = "\nConversation History:\n"
            for msg in recent_history:
                role_label = "User" if msg["role"] == "user" else "Zeyra"
                history_formatted += f"{role_label}: {msg['content']}\n"

        intent_prompt = f"""
{SYSTEM_INSTRUCTION}

{history_formatted}
User's Latest Message: "{user_text}"

Analyze the user's message and determine if an action tool is required.
Return JSON with format:
{{
  "intent": "MORNING_BRIEF" | "EXPENSE_LOG" | "INBOX_DIGEST" | "DRAFTS_DIGEST" | "SEND_DRAFT" | "SEND_EMAIL" | "REPLY_EMAIL" | "JOB_AGENT" | "CREATE_DOC" | "CREATE_SHEET" | "MANAGE_WORKSPACE_FILE" | "LIST_WORKSPACE_FILES" | "GENERAL_CONVERSATION",
  "expense_details": "Extracted expense text if intent is EXPENSE_LOG, else empty string",
  "draft_id": "Extracted draft ID if intent is SEND_DRAFT, else empty string",
  "to_email": "Extracted recipient email address, brand name, or sender keyword (e.g. 'duolingo', 'zeusmr777@gmail.com', 'linkedin') if intent is SEND_EMAIL or REPLY_EMAIL, else empty string",
  "email_subject": "Professional email subject line if intent is SEND_EMAIL or REPLY_EMAIL, else empty string",
  "email_body": "Well-formatted professional email body text if intent is SEND_EMAIL, else empty string",
  "reply_instructions": "Extracted user reply instructions if intent is REPLY_EMAIL, else empty string",
  "doc_title": "Extracted document or spreadsheet title if intent is CREATE_DOC, CREATE_SHEET, or MANAGE_WORKSPACE_FILE, else empty string",
  "doc_instructions": "Extracted instructions or content details if intent is CREATE_DOC or CREATE_SHEET, else empty string",
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

            final_reply = base_response

            # 2. Execute Action Tools based on intent
            if intent == "MORNING_BRIEF":
                brief_content = self.pa_service.get_morning_briefing()
                final_reply = f"{base_response}\n\n{brief_content}"

            elif intent == "EXPENSE_LOG":
                exp_data = self.pa_service.process_expense(expense_text)
                final_reply = (
                    f"Receipt/Expense logged! 🧾\n\n"
                    f"• *Vendor*: {exp_data.get('vendor')}\n"
                    f"• *Amount*: {exp_data.get('currency')} {exp_data.get('amount')}\n"
                    f"• *Category*: {exp_data.get('category')}\n"
                    f"• *Date*: {exp_data.get('date')}\n"
                    f"• *Details*: {exp_data.get('description')}"
                )

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

                if target_email and "@" in target_email:
                    res = self.pa_service.send_email(
                        to_email=target_email,
                        subject=target_subj,
                        body_text=email_body_val
                    )
                    if res.get("success"):
                        final_reply = (
                            f"📧 *Email Sent Successfully!*\n\n"
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
                    final_reply = (
                        f"📊 *Google Sheet Created Successfully!*\n\n"
                        f"• *Title*: {res.get('title')}\n"
                        f"• *Spreadsheet ID*: `{res.get('spreadsheet_id')}`\n"
                        f"🔗 *Open/Edit Spreadsheet*: {res.get('url')}"
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

            elif intent == "JOB_AGENT":
                final_reply = f"🚀 Running Job Application Agent for you now...\n"
                try:
                    run_job_agent(limit=1)
                    final_reply += "✅ Job application process complete! Tailored resume compiled to `Muhammad_Hamza_CV.pdf` and draft updated in Gmail."
                except Exception as e:
                    final_reply += f"⚠️ Job agent run failed: {e}"

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
