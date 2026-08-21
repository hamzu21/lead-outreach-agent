import requests
from bs4 import BeautifulSoup

def check_job_active_status(job_url: str) -> dict:
    """
    Visits the provided Job URL and checks if the job listing is currently active.
    Handles login/signup gated pages gracefully for headless 24/7 cloud execution.
    Returns dict: {"is_active": bool, "status_text": str, "description": str}
    """
    if not job_url or not job_url.startswith("http"):
        return {"is_active": False, "status_text": "Invalid Job URL", "description": ""}

    try:
        res = requests.get(
            job_url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        if res.status_code == 404:
            return {"is_active": False, "status_text": "Expired / 404 Not Found", "description": ""}
        if res.status_code >= 400:
            return {"is_active": False, "status_text": f"HTTP {res.status_code} Error", "description": ""}

        soup = BeautifulSoup(res.text, "html.parser")
        text_content = soup.get_text(separator=" ", strip=True)
        lower_text = text_content.lower()

        # Keywords indicating closed / expired job listings
        closed_keywords = [
            "no longer accepting applications",
            "job listing has expired",
            "position has been filled",
            "this job is closed",
            "page not found",
            "no longer active"
        ]

        for kw in closed_keywords:
            if kw in lower_text:
                return {
                    "is_active": False,
                    "status_text": f"Expired ({kw})",
                    "description": text_content[:2000]
                }

        # Check for signup / login wall
        login_keywords = ["sign in to apply", "log in to apply", "create an account to apply", "join to apply"]
        is_gated = any(kw in lower_text for kw in login_keywords) or "login" in res.url.lower() or "signup" in res.url.lower()

        if is_gated:
            return {
                "is_active": True,
                "status_text": "Active (Signup / Login Required)",
                "description": text_content[:2500] if len(text_content) > 100 else "Login required portal."
            }

        return {
            "is_active": True,
            "status_text": "Active",
            "description": text_content[:3000]
        }
    except Exception as e:
        # Fallback to active so headless 24/7 run generates resume draft package using sheet metadata
        return {"is_active": True, "status_text": f"Active (Cloud Note: {e})", "description": ""}
