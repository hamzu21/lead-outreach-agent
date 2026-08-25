import urllib.request
import urllib.parse
import re
import json
from src.services.ai_generator import generate_ai_content
from src.services.workspace_service import create_google_doc

def scrape_website_diagnostics(url: str) -> dict:
    """
    Fetches website HTML and extracts diagnostic metadata.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    parsed_domain = urllib.parse.urlparse(url).netloc or url
    diagnostics = {
        "url": url,
        "domain": parsed_domain,
        "is_https": url.startswith("https://"),
        "title": "N/A",
        "meta_description": "N/A",
        "h1_tags": [],
        "text_sample": ""
    }

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            diagnostics["title"] = title_match.group(1).strip()

        # Extract meta description
        meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE | re.DOTALL)
        if meta_match:
            diagnostics["meta_description"] = meta_match.group(1).strip()

        # Extract H1 tags
        h1_matches = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        diagnostics["h1_tags"] = [re.sub(r"<[^>]+>", "", h).strip() for h in h1_matches[:3]]

        # Clean text sample
        clean_text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
        clean_text = re.sub(r"<style[^>]*>.*?</style>", "", clean_text, flags=re.IGNORECASE | re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean_text)
        clean_text = " ".join(clean_text.split())
        diagnostics["text_sample"] = clean_text[:1500]

    except Exception as e:
        print(f"[WebsiteAudit] Warning scraping {url}: {e}")
        diagnostics["scrape_error"] = str(e)

    return diagnostics

def audit_website_and_pitch(docs_service, drive_service, url: str) -> dict:
    """
    Scrapes website diagnostics, uses Gemini to analyze UI/UX/SEO flaws,
    generates a Google Doc audit report and a high-converting cold email pitch.
    """
    diagnostics = scrape_website_diagnostics(url)
    domain = diagnostics.get("domain", url)

    prompt = f"""
You are a senior full-stack web developer and conversion optimization consultant auditing a client website.

Target Website URL: {diagnostics.get('url')}
Domain Name: {domain}
Is HTTPS Secure: {diagnostics.get('is_https')}
Page Title: {diagnostics.get('title')}
Meta Description: {diagnostics.get('meta_description')}
H1 Headers: {json.dumps(diagnostics.get('h1_tags'))}
Scraped Text Sample: "{diagnostics.get('text_sample')}"

Please generate a comprehensive 2-part report:

PART 1: EXECUTIVE WEBSITE AUDIT REPORT
- Overview & First Impression
- Identified Technical & UX Flaws (e.g. Mobile viewport, SEO structure, conversion call-to-action gaps)
- 3 Recommended Upgrades / Fixes to Boost Conversions & Traffic

PART 2: HIGH-CONVERTING COLD SALES EMAIL PITCH
Write a personalized, friendly, non-spammy cold email addressed to the business owner highlighting 2 specific improvement areas and offering a 15-minute quick call/meeting.

Do not wrap in markdown code blocks. Return plain document text with clear headings.
"""

    audit_text = generate_ai_content(prompt)
    doc_title = f"Website Audit & Cold Pitch - {domain}"

    # Create Google Doc report
    doc_res = create_google_doc(docs_service, drive_service, title=doc_title, content_text=audit_text)
    doc_url = doc_res.get("url") if doc_res.get("success") else f"Doc creation fallback for {domain}"

    return {
        "success": True,
        "domain": domain,
        "url": diagnostics.get("url"),
        "doc_title": doc_title,
        "doc_url": doc_url,
        "audit_text": audit_text
    }
