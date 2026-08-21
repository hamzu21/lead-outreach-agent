import requests
from bs4 import BeautifulSoup

def check_job_active_status(job_url: str) -> dict:
    """
    Visits the provided Job URL and checks if the job listing is currently active.
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

        return {
            "is_active": True,
            "status_text": "Active",
            "description": text_content[:3000]
        }
    except Exception as e:
        # Fallback to active if network error occurs so manual application can proceed
        return {"is_active": True, "status_text": f"Active (Check Note: {e})", "description": ""}
