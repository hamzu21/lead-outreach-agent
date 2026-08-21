import os
import json
import shutil
import subprocess
from google import genai
from src.config import GEMINI_API_KEY, AI_MODEL_NAME

def get_ai_client():
    return genai.Client(api_key=GEMINI_API_KEY)

def load_master_tex() -> str:
    tex_path = "resume.tex"
    if os.path.exists(tex_path):
        with open(tex_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def load_user_profile() -> dict:
    profile_path = "user_profile.json"
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def tailor_latex_code(job_title: str, company: str, tech_stack: str, job_desc: str) -> str:
    """
    Uses Gemini AI to rewrite resume.tex source code tailored for the specific job.
    """
    master_tex = load_master_tex()
    profile = load_user_profile()

    prompt = f"""
You are an expert technical resume writer and LaTeX engineer. Your task is to update and tailor a master LaTeX resume (.tex code) for a specific job application.

Job Details:
- Role Title: {job_title}
- Company: {company}
- Core Tech Stack: {tech_stack}
- Job Description snippet: {job_desc[:1500]}

Candidate Master Profile:
{json.dumps(profile, indent=2)}

Master LaTeX Source Code:
```latex
{master_tex}
```

Instructions:
1. Retain all valid LaTeX document structure, preamble, packages, and center header (Muhammad Hamza, Location: Pakistan, Email, Phone, Portfolio: https://mrhamza.dev).
2. Tailor the "Professional Summary" section to specifically target the {job_title} role at {company}, emphasizing {tech_stack}.
3. Update the "Technical Skills" section to highlight technologies matching {tech_stack} and job requirements.
4. Customize work experience bullet points to match keywords from the job description while remaining truthful to candidate profile.
5. Return ONLY the raw valid LaTeX code without markdown block fences or commentary.
"""
    client = get_ai_client()
    response = client.models.generate_content(
        model=AI_MODEL_NAME,
        contents=prompt
    )

    clean_code = response.text.strip()
    if clean_code.startswith("```latex"):
        clean_code = clean_code[8:]
    elif clean_code.startswith("```"):
        clean_code = clean_code[3:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]

    return clean_code.strip()

def compile_tex_to_pdf(tex_code: str, output_filename: str = "Muhammad_Hamza_CV.pdf") -> str:
    """
    Compiles LaTeX code into PDF. If pdflatex command line is present, executes pdflatex.
    Otherwise uses ReportLab PDF builder fallback to output a professional PDF named 'output_filename'.
    """
    temp_tex = "temp_resume.tex"
    with open(temp_tex, "w", encoding="utf-8") as f:
        f.write(tex_code)

    # Check if pdflatex CLI tool is installed
    pdflatex_bin = shutil.which("pdflatex")
    if pdflatex_bin:
        try:
            cmd = [pdflatex_bin, "-interaction=nonstopmode", "-jobname=Muhammad_Hamza_CV", temp_tex]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if os.path.exists("Muhammad_Hamza_CV.pdf"):
                return os.path.abspath("Muhammad_Hamza_CV.pdf")
        except Exception as e:
            print(f"pdflatex execution warning: {e}. Using PDF generator fallback...")

    # Fallback: Produce high-quality PDF named Muhammad_Hamza_CV.pdf
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib import colors

        pdf_path = os.path.abspath(output_filename)
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=20,
            leading=24,
            alignment=1,
            textColor=colors.HexColor("#1A365D")
        )
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#2D3748")
        )
        section_style = ParagraphStyle(
            'SectionHead',
            parent=styles['Heading2'],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1A365D"),
            spaceBefore=8,
            spaceAfter=4
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#2D3748")
        )

        profile = load_user_profile()
        story.append(Paragraph(f"<b>{profile.get('name', 'Muhammad Hamza')}</b>", title_style))
        story.append(Paragraph(f"{profile.get('title', 'Full-Stack Web Developer')} | Location: {profile.get('location', 'Pakistan')}<br/>Email: {profile.get('email')} | Phone: {profile.get('phone')} | Portfolio: {profile.get('portfolio')}", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=8))

        story.append(Paragraph("<b>PROFESSIONAL SUMMARY</b>", section_style))
        story.append(Paragraph(profile.get("summary", ""), body_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("<b>TECHNICAL SKILLS</b>", section_style))
        skills_str = ", ".join(profile.get("skills", []))
        story.append(Paragraph(f"<b>Core Technologies:</b> {skills_str}", body_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("<b>PROFESSIONAL EXPERIENCE</b>", section_style))
        for exp in profile.get("experience", []):
            story.append(Paragraph(f"<b>{exp.get('role')}</b> — {exp.get('company')} ({exp.get('period')})", body_style))
            for h in exp.get("highlights", []):
                story.append(Paragraph(f"• {h}", body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        return pdf_path
    except Exception as e:
        print(f"Error generating PDF fallback: {e}")

    return ""

def generate_tailored_resume_pdf(job_title: str, company: str, tech_stack: str, job_desc: str, output_filename: str = "Muhammad_Hamza_CV.pdf") -> str:
    """
    Main helper: tailors LaTeX code via Gemini AI and compiles to Muhammad_Hamza_CV.pdf.
    """
    tex_code = tailor_latex_code(job_title, company, tech_stack, job_desc)
    pdf_path = compile_tex_to_pdf(tex_code, output_filename=output_filename)
    return pdf_path
