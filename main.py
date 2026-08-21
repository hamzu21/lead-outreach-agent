import sys
import traceback
import argparse
from src.agent import run_agent
from src.modules.job_agent.job_pipeline import run_job_agent

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent AI Executive Assistant")
    parser.add_argument(
        "--mode",
        type=str,
        default="outreach",
        choices=["outreach", "jobs"],
        help="Agent mode: 'outreach' for client lead outreach, 'jobs' for automated job application & LaTeX resume tailoring"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum items to process in single batch (default: 10 for outreach, 1 for jobs)"
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
