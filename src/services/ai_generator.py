import json
import time
from google import genai
from google.genai import errors
from src.config import (
    GEMINI_API_KEY,
    AI_MODEL_NAME,
    SENDER_NAME,
    SENDER_ROLE,
    SENDER_PHONE,
    SENDER_PORTFOLIO
)

_client = None

def get_ai_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

FALLBACK_MODELS = [
    AI_MODEL_NAME,
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest"
]

def generate_ai_content(prompt: str, response_mime_type: str = None) -> str:
    """
    Executes a Gemini AI prompt with automatic model fallback and rate limit retry handling.
    """
    client = get_ai_client()
    last_exception = None
    candidate_models = list(dict.fromkeys(FALLBACK_MODELS))

    config = {}
    if response_mime_type:
        config["response_mime_type"] = response_mime_type

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config if config else None
            )
            return response.text.strip()
        except errors.APIError as e:
            last_exception = e
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"Notice: Model {model_name} rate limited (429). Trying fallback model...")
                time.sleep(2)
                continue
            elif "404" in str(e) or "NOT_FOUND" in str(e):
                print(f"Notice: Model {model_name} not available. Trying fallback model...")
                continue
            else:
                raise e
        except Exception as e:
            last_exception = e
            continue

    if last_exception:
        raise last_exception
    raise RuntimeError("Failed to generate content with available Gemini AI models.")

def analyze_and_draft_email(lead_data: dict, web_audit: dict) -> dict:
    """
    Generates a personalized cold outreach email using Gemini AI.
    Includes automatic model fallback and rate limit retry logic.
    """
    prompt = f"""
You are an expert web development consultant drafting a high-converting, personalized cold outreach email for Muhammad Hamza ({SENDER_PORTFOLIO}).

Lead Information:
- Business Name: {lead_data.get('name')}
- Location: {lead_data.get('location')}
- Industry: {lead_data.get('industry')}
- Current Website Status: {lead_data.get('website_status')}
- Social Media: {lead_data.get('social_link')}
- Web Audit / Research: {json.dumps(web_audit)}

Requirements:
1. Subject line: Short, relevant, and specific to their business/city (no hype or generic sales words).
2. Email Body:
   - Mention their business name and local presence.
   - Point out 2-3 specific, high-impact improvements:
     * If they only have a Facebook/Google listing: Highlight missed Google Search traffic, lack of an automated 24/7 quote/booking form, and improved credibility with a dedicated site.
     * If they have an existing website: Highlight conversion bottlenecks (mobile responsiveness, slow load, booking/contact friction, outdated layout).
   - Keep tone direct, professional, and friendly.
   - State clearly that you build modern web applications and custom booking flows.
   - Include a low-friction call-to-action (e.g., offering a 2-minute visual mockup).
3. Signature block:
{SENDER_NAME}
{SENDER_ROLE}
Phone: {SENDER_PHONE}
Portfolio: {SENDER_PORTFOLIO}

Output Format (strict JSON):
{{
  "subject": "Email Subject",
  "body": "Plain text body"
}}
"""
    raw_res = generate_ai_content(prompt, response_mime_type="application/json")
    return json.loads(raw_res)
