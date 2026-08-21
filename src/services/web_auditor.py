import requests
from bs4 import BeautifulSoup

def inspect_website(url: str) -> dict:
    """
    Performs a lightweight web audit of a lead's website.
    """
    if not url or not url.startswith("http"):
        return {"exists": False, "notes": "No standalone website"}
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
        has_meta_viewport = bool(soup.find("meta", attrs={"name": "viewport"}))
        has_form = bool(soup.find("form") or soup.find("iframe"))
        text_content = soup.get_text(separator=" ", strip=True)[:1500]

        return {
            "exists": True,
            "url": url,
            "title": title,
            "mobile_friendly": has_meta_viewport,
            "has_booking_or_contact_form": has_form,
            "snippet": text_content
        }
    except Exception as e:
        return {"exists": False, "error": str(e)}
