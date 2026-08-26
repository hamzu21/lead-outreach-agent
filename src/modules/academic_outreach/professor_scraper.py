import os
import csv
import json
import re
import requests
from bs4 import BeautifulSoup
from src.services.google_auth import get_google_services
from src.services.workspace_service import create_styled_spreadsheet
from src.services.ai_generator import generate_ai_content

DEFAULT_PROFESSORS_CSV = os.path.join(os.getcwd(), "professors_list.csv")

def scrape_university_faculty_page(url: str, target_fields: str = "AI, Cyber Security, Computer Science") -> dict:
    """
    Scrapes a university faculty page, extracts professors, filters for target fields,
    generates a styled Google Spreadsheet on Google Drive, appends to local professors_list.csv,
    and returns a clean, clickable Google Sheets URL.
    """
    print(f"[FacultyScraper] Fetching university faculty page: {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    page_html = ""
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            page_html = res.text
    except Exception as e:
        print(f"[FacultyScraper] HTTP fetch error: {e}")

    # Extract text content from HTML
    soup = BeautifulSoup(page_html if page_html else "<html></html>", "html.parser")
    for s in soup(["script", "style", "nav", "footer"]):
        s.decompose()
    
    raw_text = soup.get_text(separator="\n", strip=True)
    text_snippet = raw_text[:20000]

    print(f"[FacultyScraper] Extracting professors for fields '{target_fields}' using Gemini AI...")
    
    prompt = f"""
You are an expert academic research crawler. Extract faculty members / professors from the following university webpage text snippet.

Webpage URL: {url}
Target Research Fields / Topics: {target_fields}

Webpage Content Snippet:
{text_snippet}

Requirements:
1. Identify faculty members (Professors, Associate Professors, Assistant Professors, Lab Directors).
2. Extract:
   - "university": University Name (e.g. KAUST / King Abdullah University of Science and Technology)
   - "country": Country (e.g. Saudi Arabia, USA, Canada, Germany)
   - "name": Full Name (e.g. Prof. Bernard Ghanem)
   - "email": Email address if found in snippet, else construct plausible academic email format (e.g. firstname.lastname@kaust.edu.sa) or empty string
   - "research_topic": Specific research area / field (e.g. Computer Vision, Cybersecurity, AI, Machine Learning)
   - "profile_url": Link to profile or webpage URL

Return strict JSON:
{{
  "university_name": "University Name",
  "country": "Country",
  "professors": [
    {{
      "name": "Prof. John Doe",
      "email": "john.doe@university.edu",
      "research_topic": "Artificial Intelligence & Computer Vision",
      "profile_url": "{url}"
    }}
  ]
}}
"""
    professors = []
    univ_name = "University Faculty"
    country_name = "Global"

    try:
        raw_json = generate_ai_content(prompt, response_mime_type="application/json")
        clean_str = raw_json.strip().strip("`").replace("json\n", "")
        extracted_data = json.loads(clean_str)
        
        if isinstance(extracted_data, list):
            professors = extracted_data
            univ_name = "KAUST / University Faculty"
            country_name = "Saudi Arabia" if "kaust" in url.lower() else "Global"
        elif isinstance(extracted_data, dict):
            univ_name = extracted_data.get("university_name", "University Faculty")
            country_name = extracted_data.get("country", "Global")
            professors = extracted_data.get("professors", [])
    except Exception as ex:
        print(f"[FacultyScraper] Error parsing Gemini faculty JSON: {ex}")

    if not professors:
        print("[FacultyScraper] Fallback: Using regex pattern extraction...")
        pattern = r"(Prof\.|Dr\.|Doctor)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)"
        matches = re.findall(pattern, raw_text)
        for title, p_name in matches[:10]:
            professors.append({
                "name": f"{title} {p_name}",
                "email": "",
                "research_topic": target_fields,
                "profile_url": url
            })

    if not professors:
        return {
            "success": False,
            "error": f"Could not automatically extract faculty listings from {url}. Please verify URL or permissions."
        }

    # 1. Generate formatted Google Spreadsheet on Google Drive
    sheets_service, gmail_service, docs_service, drive_service = get_google_services()
    sheet_title = f"{univ_name} Professors - {target_fields}"
    
    headers = ["University", "Country", "Name", "Email", "Research Topic", "Faculty Profile", "Status"]
    rows = []
    
    for p in professors:
        rows.append([
            univ_name,
            country_name,
            p.get("name", "Professor"),
            p.get("email", ""),
            p.get("research_topic", target_fields),
            p.get("profile_url", url),
            "Pending"
        ])

    sheet_url = ""
    sheet_id = ""
    if sheets_service and drive_service:
        try:
            res_sheet = create_styled_spreadsheet(
                sheets_service,
                drive_service,
                title=sheet_title,
                headers=headers,
                rows=rows,
                theme_color="blue"
            )
            if res_sheet.get("success"):
                sheet_url = res_sheet.get("url")
                sheet_id = res_sheet.get("spreadsheet_id")
                print(f"[FacultyScraper] Created Google Sheet: {sheet_url}")
        except Exception as se:
            print(f"[FacultyScraper] Error creating Google Sheet: {se}")

    # 2. Append to local professors_list.csv so the outreach agent can use them
    try:
        csv_file = DEFAULT_PROFESSORS_CSV
        file_exists = os.path.exists(csv_file)
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['University', 'Country', 'Name', 'Email', 'Research_Topic', 'Latest_Paper', 'Status']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            for p in professors:
                writer.writerow({
                    'University': univ_name,
                    'Country': country_name,
                    'Name': p.get("name", "Professor"),
                    'Email': p.get("email", ""),
                    'Research_Topic': p.get("research_topic", target_fields),
                    'Latest_Paper': '',
                    'Status': 'Pending'
                })
        print(f"[FacultyScraper] Appended {len(professors)} professors to local CSV: {csv_file}")
    except Exception as ce:
        print(f"[FacultyScraper] Notice updating local CSV: {ce}")

    return {
        "success": True,
        "university": univ_name,
        "country": country_name,
        "target_fields": target_fields,
        "count": len(professors),
        "professors": professors,
        "url": sheet_url,
        "sheet_id": sheet_id
    }
