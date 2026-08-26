import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from src.services.ai_generator import generate_ai_content

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def extract_clean_search_query(user_text: str, history_context: str = "") -> str:
    """
    Uses Gemini AI to extract an optimized, clean English search query
    from conversational input, utilizing conversation history to resolve pronouns/subjects.
    """
    prompt = f"""
Convert this user's conversational message into a clean, concise, keyword-focused Google/web search query.

{history_context if history_context else 'No previous conversation history.'}

User's Current Message: "{user_text}"

Rules:
- Return ONLY the clean search query string (no explanation, no punctuation, no quotes).
- Use previous conversation history if the current message refers to a previous subject (e.g., if history was about gold rates and user says "mjhe exact rate btao", output "gold price per tola today Pakistan PKR").
- Examples:
  "aaj gold ka lya rate hai?" -> "gold price per tola today Pakistan"
  "mjhe exact rate btao" (history about gold) -> "gold price per tola today Pakistan PKR"
  "live new test kro" -> "latest breaking news Pakistan today"
  "mere baare mein search krke dekho mr hamza dev" -> "mr hamza dev developer"
"""
    try:
        clean_q = generate_ai_content(prompt).strip().strip('"').strip("'")
        return clean_q if clean_q else user_text
    except Exception as e:
        print(f"[WebSearch] Error extracting query: {e}")
        return user_text

def search_duckduckgo_lite(query: str, max_results: int = 5) -> list:
    """
    Scrapes DuckDuckGo Lite HTML for lightweight, high-reliability search results.
    """
    results = []
    try:
        url = "https://lite.duckduckgo.com/lite/"
        res = requests.post(url, data={"q": query}, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            snippets = soup.find_all("td", class_="result-snippet")
            links = soup.find_all("a", class_="result-link")
            
            for i in range(min(len(links), max_results)):
                t = links[i].get_text(strip=True)
                l = links[i].get("href", "")
                s = snippets[i].get_text(strip=True) if i < len(snippets) else ""
                results.append({"title": t, "link": l, "snippet": s})
    except Exception as e:
        print(f"[WebSearch] DuckDuckGo Lite search error: {e}")
    return results

def search_google_news_rss(query: str, max_results: int = 5) -> list:
    """
    Queries Google News RSS Feed for live news, market rates, and current events.
    """
    results = []
    try:
        encoded_q = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-PK&gl=PK&ceid=PK:en"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "xml")
            items = soup.find_all("item")
            for item in items[:max_results]:
                title = item.title.get_text(strip=True) if item.title else "News Article"
                link = item.link.get_text(strip=True) if item.link else ""
                desc = item.description.get_text(strip=True) if item.description else title
                results.append({"title": title, "link": link, "snippet": desc})
    except Exception as e:
        print(f"[WebSearch] Google News RSS error: {e}")
    return results

def fetch_webpage_text(url: str, max_chars: int = 3000) -> str:
    """
    Fetches live webpage text from any given URL.
    """
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return f"Failed to load URL (HTTP {res.status_code})"

        soup = BeautifulSoup(res.text, "html.parser")
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()

        text = soup.get_text(separator=" ", strip=True)
        return text[:max_chars]
    except Exception as e:
        return f"Error fetching webpage: {e}"

def perform_realtime_web_browsing(user_text: str, history_context: str = "") -> str:
    """
    Extracts search query (using history for context), queries DuckDuckGo & Google News, and generates a warm, synthesized answer.
    """
    is_url = user_text.strip().startswith("http://") or user_text.strip().startswith("https://")
    
    if is_url:
        target_url = user_text.strip()
        page_text = fetch_webpage_text(target_url)
        prompt = f"""
You are Zeyra, reading a live webpage in real-time for Hamza.

Webpage URL: {target_url}
Webpage Content Snippet:
{page_text}

Provide a clean, warm, executive summary of what this webpage contains. Cite key takeaways clearly.
"""
        return generate_ai_content(prompt)

    # 1. Extract clean Google search query from user text using history context
    clean_query = extract_clean_search_query(user_text, history_context)
    print(f"[WebSearch] Original Input: '{user_text}' -> Extracted Query: '{clean_query}'")

    # 2. Perform search via DuckDuckGo Lite & Google News RSS
    results = search_duckduckgo_lite(clean_query, max_results=5)
    if not results:
        results = search_google_news_rss(clean_query, max_results=5)

    if not results:
        return "🔍 *Real-Time Web Search*: Main ne internet par search kiya par abhi koi direct relevant results nahi miley. Kuch aur specific search query bolein?"

    prompt = f"""
You are Zeyra, providing direct real-time web search results to Hamza.

{history_context if history_context else ''}

User's Current Question: "{user_text}"
Search Keywords Used: "{clean_query}"

Live Search Results:
{json.dumps(results, indent=2)}

STRICT INSTRUCTIONS FOR DIRECT RESPONSE:
- State the EXACT answer, figures, or live market data IMMEDIATELY in your VERY FIRST sentence!
- DO NOT output filler chatter (NEVER say "Bilkul Hamza!", "Main check karti hoon", "Let me search right away!", "Chalo check kartay hain!").
- DO NOT invent fake AI disclaimers or excuses (NEVER say "due to security/privacy reasons", "cannot share exact figures in public chat", "visit customer portal", or "contact support").
- NEVER say "pehle koi baat nahi hui" or "yeh pehla message hai".
- Summarize the exact numbers, rates, or news clearly in crisp, direct Roman Urdu/English.
"""

    answer = generate_ai_content(prompt)
    return answer
