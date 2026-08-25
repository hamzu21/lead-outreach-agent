import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from src.services.ai_generator import generate_ai_content

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_web(query: str, max_results: int = 5) -> dict:
    """
    Performs real-time web search using DuckDuckGo HTML API and returns search results.
    """
    encoded_query = quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        if response.status_code != 200:
            return {"success": False, "error": f"Search HTTP {response.status_code}", "results": []}

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.find_all("div", class_="result"):
            if len(results) >= max_results:
                break
            
            title_tag = result.find("a", class_="result__a")
            snippet_tag = result.find("a", class_="result__snippet")
            
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet
                })

        return {"success": True, "query": query, "results": results}
    except Exception as e:
        print(f"[WebSearchService] Search error: {e}")
        return {"success": False, "error": str(e), "results": []}

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

def perform_realtime_web_browsing(query_or_url: str) -> str:
    """
    Performs real-time web search/browsing and uses Gemini AI to synthesize a crisp, human answer.
    """
    is_url = query_or_url.startswith("http://") or query_or_url.startswith("https://")
    
    if is_url:
        page_text = fetch_webpage_text(query_or_url)
        prompt = f"""
You are Zeyra, reading a live webpage in real-time for Hamza.

Webpage URL: {query_or_url}
Webpage Content Snippet:
{page_text}

Provide a clean, warm, executive summary of what this webpage contains. Cite key takeaways clearly.
"""
    else:
        search_res = search_web(query_or_url)
        results = search_res.get("results", [])
        
        if not results:
            return "🔍 *Real-Time Web Search*: Main ne internet par search kiya par abhi koi direct relevant results nahi miley. Kuch aur query search karoon?"

        prompt = f"""
You are Zeyra, performing real-time web browsing to answer Hamza's query.

User Query: "{query_or_url}"

Real-Time Web Search Results:
{json.dumps(results, indent=2)}

Provide a clear, accurate, up-to-date, and human-like answer synthesizing these live web search results. Cite key sources/links if relevant.
"""

    answer = generate_ai_content(prompt)
    return answer
