import os
import json
import shutil
import requests
import subprocess
from src.services.ai_generator import generate_ai_content

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
1. Preserve the exact LaTeX preamble, document class (resume), packages, macros, and section formatting.
2. Tailor the "Profile Summary" section to specifically target the {job_title} role at {company}, emphasizing {tech_stack}.
3. Update the "Technical Skills" section to highlight technologies matching {tech_stack} and job requirements.
4. Customize work experience bullet points to match keywords from the job description while remaining truthful to candidate profile.
5. Return ONLY raw valid LaTeX code without markdown block fences or commentary.
"""
    clean_code = generate_ai_content(prompt)

    if clean_code.startswith("```latex"):
        clean_code = clean_code[8:]
    elif clean_code.startswith("```"):
        clean_code = clean_code[3:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]

    return clean_code.strip()

def compile_tex_to_pdf(tex_code: str, output_filename: str = "Muhammad_Hamza_CV.pdf") -> str:
    """
    Compiles LaTeX code into native LaTeX PDF.
    1. Tries local pdflatex CLI.
    2. Tries native online LaTeX compiler API (ytotech) with resume.cls for pixel-perfect LaTeX output matching Hamza_Resume.pdf.
    3. ReportLab fallback.
    """
    temp_tex = "temp_resume.tex"
    with open(temp_tex, "w", encoding="utf-8") as f:
        f.write(tex_code)

    pdf_target_path = os.path.abspath(output_filename)

    # 1. Try local pdflatex CLI
    pdflatex_bin = shutil.which("pdflatex")
    if pdflatex_bin:
        try:
            cmd = [pdflatex_bin, "-interaction=nonstopmode", "-jobname=Muhammad_Hamza_CV", temp_tex]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if os.path.exists("Muhammad_Hamza_CV.pdf"):
                return pdf_target_path
        except Exception as e:
            print(f"Notice: Local pdflatex execution warning: {e}. Trying online LaTeX compiler API...")

    # 2. Try Native Online LaTeX Compiler API (ytotech)
    try:
        cls_content = ""
        if os.path.exists("resume.cls"):
            with open("resume.cls", "r", encoding="utf-8") as f:
                cls_content = f.read()

        payload = {
            "compiler": "pdflatex",
            "resources": [
                {"main": True, "content": tex_code},
                {"main": False, "path": "resume.cls", "content": cls_content}
            ]
        }
        res = requests.post("https://latex.ytotech.com/builds/sync", json=payload, timeout=25)
        if res.status_code in [200, 201] and len(res.content) > 1000:
            with open(pdf_target_path, "wb") as f:
                f.write(res.content)
            print(f"-> Successfully compiled native LaTeX resume to {output_filename} ({len(res.content)} bytes)")
            return pdf_target_path
        else:
            print(f"Notice: Online LaTeX API returned status {res.status_code}. Using fallback...")
    except Exception as e:
        print(f"Notice: Online LaTeX API call failed: {e}. Using ReportLab fallback...")

    # 3. ReportLab Fallback
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib import colors

        doc = SimpleDocTemplate(pdf_target_path, pagesize=letter, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, textColor=colors.HexColor("#000000"))
        subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontSize=9.5, leading=13, alignment=1, textColor=colors.HexColor("#222222"))
        section_style = ParagraphStyle('SectionHead', parent=styles['Heading2'], fontSize=11, leading=15, textColor=colors.HexColor("#000000"), spaceBefore=6, spaceAfter=2)
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9.5, leading=13, textColor=colors.HexColor("#111111"))

        profile = load_user_profile()
        story.append(Paragraph(f"<b>{profile.get('name', 'MUHAMMAD HAMZA').upper()}</b>", title_style))
        story.append(Paragraph(f"{profile.get('phone')} &diamond; {profile.get('location')}<br/><a href='mailto:{profile.get('email')}'>{profile.get('email')}</a> | <a href='{profile.get('linkedin')}'>linkedin</a> | <a href='{profile.get('github')}'>github</a> | <a href='{profile.get('portfolio')}'>Portfolio</a>", subtitle_style))
        story.append(Spacer(1, 4))

        story.append(Paragraph("<b>PROFILE SUMMARY</b>", section_style))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.black, spaceAfter=4))
        story.append(Paragraph(profile.get("summary", ""), body_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("<b>EXPERIENCE</b>", section_style))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.black, spaceAfter=4))
        for exp in profile.get("experience", []):
            story.append(Paragraph(f"<b>{exp.get('role')}</b> — {exp.get('company')} ({exp.get('period')})", body_style))
            for h in exp.get("highlights", []):
                story.append(Paragraph(f"• {h}", body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        return pdf_target_path
    except Exception as e:
        print(f"Error generating PDF fallback: {e}")

    return ""

def generate_tailored_resume_pdf(job_title: str, company: str, tech_stack: str, job_desc: str, output_filename: str = "Muhammad_Hamza_CV.pdf") -> str:
    """
    Main helper: tailors LaTeX code via Gemini AI and compiles to native LaTeX PDF named output_filename.
    """
    tex_code = tailor_latex_code(job_title, company, tech_stack, job_desc)
    pdf_path = compile_tex_to_pdf(tex_code, output_filename=output_filename)
    return pdf_path
