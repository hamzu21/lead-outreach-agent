import argparse
from src.agent import run_agent

def main():
    parser = argparse.ArgumentParser(description="Lead Outreach AI Agent")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of lead emails to draft in a single batch (default: 10)"
    )
    args = parser.parse_args()

    print(f"Starting Lead Outreach Agent (Batch Limit: {args.limit})...")
    run_agent(limit=args.limit)

if __name__ == "__main__":
    main()
