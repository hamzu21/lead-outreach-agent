import sys
import traceback
import argparse
from src.agent import run_agent
from src.modules.job_agent.job_pipeline import run_job_agent
from src.modules.personal_assistant import (
    run_morning_brief_agent,
    run_expense_tracker_agent,
    run_inbox_zero_agent
)
from src.modules.academic_outreach import run_academic_outreach_campaign

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent AI Executive Assistant")
    parser.add_argument(
        "--mode",
        type=str,
        default="outreach",
        choices=["outreach", "jobs", "academic", "professor", "morning_brief", "expense_tracker", "inbox_zero", "bot"],
        help="Agent mode: 'outreach', 'jobs', 'academic', 'professor', 'morning_brief', 'expense_tracker', 'inbox_zero', 'bot'"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum items to process in single batch"
    )
    parser.add_argument(
        "--text",
        type=str,
        default="",
        help="Input text string for expense_tracker mode (e.g. --text 'Paid 50$ for AWS')"
    )
    args = parser.parse_args()

    if args.mode == "jobs":
        limit = args.limit if args.limit is not None else 1
        print(f"Starting Job Application Agent (Mode: jobs, Limit: {limit})...")
        try:
            run_job_agent(limit=limit)
        except Exception as e:
            print(f"\n[ERROR] Job Application Agent failed: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    elif args.mode == "morning_brief":
        print("Starting Morning Executive Briefing Agent...")
        try:
            run_morning_brief_agent(send_telegram=True)
        except Exception as e:
            print(f"\n[ERROR] Morning Briefing Agent failed: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    elif args.mode == "expense_tracker":
        input_text = args.text or "Paid $25 for meal"
        print(f"Starting Expense Tracker Agent (Input: '{input_text}')...")
        try:
            run_expense_tracker_agent(input_text, send_telegram=True)
        except Exception as e:
            print(f"\n[ERROR] Expense Tracker Agent failed: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    elif args.mode == "inbox_zero":
        print("Starting Inbox Zero / Digest Agent...")
        try:
            run_inbox_zero_agent(send_telegram=True)
        except Exception as e:
            print(f"\n[ERROR] Inbox Zero Agent failed: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    elif args.mode in ["academic", "professor"]:
        limit = args.limit if args.limit is not None else 10
        print(f"Starting Academic Professor Outreach Agent (Mode: {args.mode}, Limit: {limit})...")
        try:
            res = run_academic_outreach_campaign(limit=limit)
            print(f"[SUCCESS] Academic Outreach Campaign Completed! Processed: {res.get('processed_count')} professors.")
        except Exception as e:
            print(f"\n[ERROR] Academic Outreach Agent failed: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    elif args.mode == "bot":
        print("Starting Interactive Telegram Bot Listener...")
        try:
            run_telegram_bot_loop()
        except Exception as e:
            print(f"\n[ERROR] Telegram Bot failed: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    else:
        limit = args.limit if args.limit is not None else 10
        print(f"Starting Lead Outreach Agent (Mode: outreach, Limit: {limit})...")
        try:
            run_agent(limit=limit)
        except Exception as e:
            print(f"\n[ERROR] Lead Outreach Agent failed: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()
