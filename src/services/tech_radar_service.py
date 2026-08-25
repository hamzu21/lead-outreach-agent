import datetime
from src.services.ai_generator import generate_ai_content

def generate_tech_radar_briefing() -> str:
    """
    Generates a daily executive AI Tech Radar briefing containing high-demand client tech skills,
    micro-SaaS ideas, and developer industry trends.
    """
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    prompt = f"""
You are an executive technology strategist and tech market analyst preparing a daily Tech Radar briefing for Muhammad Hamza (Full-Stack & AI Solutions Engineer).

Today's Date: {today_str}

Generate a punchy, highly practical Telegram briefing formatted in Markdown:

📡 *DAILY TECH RADAR & MICRO-SAAS BRIEFING ({today_str})*

⚡ *Top 3 High-Demand Client Tech Stacks Today*:
1. [Tech Stack 1 + Why Clients Are Hiring]
2. [Tech Stack 2 + Why Clients Are Hiring]
3. [Tech Stack 3 + Why Clients Are Hiring]

💡 *Top 3 Micro-SaaS Ideas for Solo Developers*:
1. 🚀 *Idea Name*: Brief description + Target Audience + Revenue Model
2. 🚀 *Idea Name*: Brief description + Target Audience + Revenue Model
3. 🚀 *Idea Name*: Brief description + Target Audience + Revenue Model

🛠️ *Dev Tool / AI Trend of the Day*:
• [Tool / Trend Name & Quick Value Pitch]

Keep formatting clean with bold text and emojis. Punchy and actionable!
"""

    return generate_ai_content(prompt)
