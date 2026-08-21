"""
Backward-compatibility wrapper for lead_agent.py.
Imports and delegates execution to the modular src package.
"""
import sys
from src.agent import run_agent

if __name__ == "__main__":
    limit = 5
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    run_agent(limit=limit)