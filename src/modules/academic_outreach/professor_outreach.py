import os
import csv
import json
import time
import requests
from src.services.google_auth import get_google_services
from src.services.gmail_service import send_gmail_message
from src.services.ai_generator import generate_ai_content

CV_FILE_PATH = os.path.join(os.getcwd(), "Muhammad_Hamza_CV.pdf")
DEFAULT_PROFESSORS_CSV = os.path.join(os.getcwd(), "professors_list.csv")

def fetch_semantic_scholar_paper(prof_name: str) -> str:
    """
    Fetches latest paper title for a professor using Semantic Scholar API or OpenAlex API.
    """
    print(f"[AcademicOutreach] Searching Semantic Scholar for: {prof_name}...")
    try:
        url = f"https://api.semanticscholar.org/graph/v1/author/search?query={requests.utils.quote(prof_name)}&fields=name,papers.title,papers.year"
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                author = data['data'][0]
                papers = author.get('papers', [])
                valid_papers = [p for p in papers if p.get('year') and p.get('title')]
                valid_papers.sort(key=lambda x: x['year'], reverse=True)
                if valid_papers:
                    latest_paper = valid_papers[0]['title']
                    print(f"-> Found paper on Semantic Scholar: '{latest_paper[:60]}...'")
                    return latest_paper
    except Exception as e:
        print(f"[AcademicOutreach] Semantic Scholar lookup notice: {e}")

    # Fallback to OpenAlex API
    try:
        print(f"[AcademicOutreach] Fallback: Searching OpenAlex for {prof_name}...")
        url = f"https://api.openalex.org/works?filter=author.researcher_id:{requests.utils.quote(prof_name)}&sort=publication_year:desc&per_page=1"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            if results and results[0].get("title"):
                latest_paper = results[0].get("title")
                print(f"-> Found paper on OpenAlex: '{latest_paper[:60]}...'")
                return latest_paper
    except Exception as ex:
        print(f"[AcademicOutreach] OpenAlex lookup notice: {ex}")

    return None

def build_academic_email_body(prof_name: str, university: str, research_topic: str, paper_title: str = None) -> dict:
    """
    Generates a personalized, concise email body & subject using Gemini AI or structured template.
    """
    if paper_title:
        research_hook = f"I recently came across your published work titled \"{paper_title}\". Your methodologies and findings in this domain strongly align with my academic background and research goals."
    else:
        research_hook = f"I have been closely reviewing your lab's ongoing research in {research_topic}, which aligns directly with my technical background in AI pipelines and software engineering architectures."

    prompt = f"""
You are writing a highly professional, concise research inquiry email on behalf of Muhammad Hamza (BS IT Graduate).

Recipient: Dr./Prof. {prof_name}
University: {university}
Research Topic: {research_topic}
Paper / Research Hook: "{research_hook}"

Requirements:
1. Professional, respectful, and concise tone (under 160 words).
2. Explicitly express interest in prospective Master's/PhD research opportunities and funded graduate positions under their supervision for upcoming intake.
3. Mention hands-on background in full-stack engineering, scalable software architectures, and applied machine learning pipelines.
4. Mention attached CV for their review.

Return JSON:
{{
  "subject": "Prospective Master's Student - Research Inquiry - {prof_name}",
  "body": "Raw email body text"
}}
"""
    try:
        raw_json = generate_ai_content(prompt, response_mime_type="application/json")
        clean_str = raw_json.strip().strip("`").replace("json\n", "")
        data = json.loads(clean_str)
        return data
    except Exception as ex:
        print(f"[AcademicOutreach] Fallback template for {prof_name}: {ex}")
        body_text = f"""Dear Dr./Prof. {prof_name},

I hope this email finds you well.

My name is Muhammad Hamza, and I recently completed my BS in Information Technology. I am writing to inquire about potential Master's research opportunities and graduate positions under your supervision at {university} for the upcoming intake.

{research_hook}

My practical background includes full-stack development, scalable software architectures, and applied machine learning pipelines. I am eager to contribute to ongoing projects in your research group and pursue advanced studies in these domains.

I have attached my CV for your consideration. If you are accepting prospective graduate students, I would welcome the opportunity for a brief discussion regarding how my background could support your lab's objectives.

Thank you for your time and consideration.

Sincerely,
Muhammad Hamza
Rahim Yar Khan, Pakistan
"""
        return {
            "subject": f"Prospective Master's Student - Research Inquiry - {prof_name}",
            "body": body_text
        }

def create_sample_professors_csv(csv_path: str = DEFAULT_PROFESSORS_CSV):
    """
    Creates a sample professors_list.csv tracker if it doesn't already exist.
    """
    if os.path.exists(csv_path):
        return

    fieldnames = ['University', 'Country', 'Name', 'Email', 'Research_Topic', 'Latest_Paper', 'Status']
    sample_data = [
        {
            'University': 'Tsinghua University',
            'Country': 'China',
            'Name': 'Prof. Wei Zhang',
            'Email': 'wzhang@tsinghua.edu.cn',
            'Research_Topic': 'Artificial Intelligence & Computer Vision',
            'Latest_Paper': '',
            'Status': 'Pending'
        },
        {
            'University': 'University of Alberta',
            'Country': 'Canada',
            'Name': 'Dr. John Smith',
            'Email': 'jsmith@ualberta.ca',
            'Research_Topic': 'Machine Learning & Software Systems',
            'Latest_Paper': '',
            'Status': 'Pending'
        },
        {
            'University': 'TU Munich',
            'Country': 'Germany',
            'Name': 'Prof. Hans Meyer',
            'Email': 'meyer@in.tum.de',
            'Research_Topic': 'Distributed Systems & Cloud Computing',
            'Latest_Paper': '',
            'Status': 'Pending'
        }
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)
    print(f"[AcademicOutreach] Created sample tracker CSV: {csv_path}")

def run_academic_outreach_campaign(csv_file: str = DEFAULT_PROFESSORS_CSV, limit: int = 10) -> dict:
    """
    Main pipeline for Academic Professor Outreach Campaign.
    """
    create_sample_professors_csv(csv_file)
    
    sheets, gmail, docs, drive = get_google_services()
    if not gmail:
        return {"success": False, "error": "Gmail API authentication unavailable"}

    rows = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    sent_count = 0
    cv_path = CV_FILE_PATH if os.path.exists(CV_FILE_PATH) else None

    for idx, row in enumerate(rows):
        if sent_count >= limit:
            print(f"[AcademicOutreach] Reached limit of {limit} professors. Stopping batch.")
            break

        status = row.get('Status', '')
        if status in ['Sent', 'Draft Created']:
            continue

        prof_name = row.get('Name', 'Professor')
        prof_email = row.get('Email', '')
        university = row.get('University', 'University')
        research_topic = row.get('Research_Topic', 'Software Engineering & AI')

        if not prof_email or "@" not in prof_email:
            continue

        print(f"\n[AcademicOutreach] [{sent_count + 1}/{limit}] Processing: {prof_name} ({university})")

        # 1. Fetch Scholar Insights
        paper_title = fetch_semantic_scholar_paper(prof_name)
        row['Latest_Paper'] = paper_title if paper_title else 'N/A'

        # 2. Build Personalized Email
        email_content = build_academic_email_body(prof_name, university, research_topic, paper_title=paper_title)

        # 3. Send Email via Gmail API (with CV attachment)
        try:
            msg_id = send_gmail_message(gmail, prof_email, email_content["subject"], email_content["body"], attachment_path=cv_path)
            print(f" -> Sent email to {prof_email} (Msg ID: {msg_id})")
            row['Status'] = 'Sent'
            sent_count += 1
            time.sleep(2) # Anti-Spam pause
        except Exception as e:
            print(f" -> Error sending email to {prof_name}: {e}")
            row['Status'] = f"Failed: {e}"

    # Update CSV tracker
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['University', 'Country', 'Name', 'Email', 'Research_Topic', 'Latest_Paper', 'Status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "success": True,
        "processed_count": sent_count,
        "csv_file": csv_file
    }
