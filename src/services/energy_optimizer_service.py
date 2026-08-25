import json
from src.services.ai_generator import generate_ai_content
from src.services.time_utils import get_pkt_now_str

def optimize_daily_focus(user_note: str) -> str:
    """
    Takes user's current energy state and tasks, and generates an optimized bio-rhythm daily focus plan.
    """
    current_pkt_time = get_pkt_now_str()

    prompt = f"""
You are Zeyra, an AI Bio-Rhythm & Focus Optimizer assisting Muhammad Hamza (Full-Stack & AI Solutions Developer).

Current Time (PKT): {current_pkt_time}
User's Energy / Schedule Input: "{user_note}"

Generate an optimized Daily Focus & Energy Schedule for Hamza:
1. ⚡ *Energy State Assessment* (Evaluate mental focus window based on user input).
2. 🎯 *Task Prioritization Plan*:
   - High-Friction Coding / Architecture tasks assigned during peak energy windows.
   - Low-Friction Admin tasks (emails, reviews) assigned during low energy windows.
3. 🧘 *Health & Wellness Breaks* (Hydration, posture stretch, eye-rest intervals).

Keep output punchy, encouraging, and structured in Telegram Markdown format.
"""
    schedule = generate_ai_content(prompt)
    return schedule
