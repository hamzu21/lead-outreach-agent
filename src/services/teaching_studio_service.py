import datetime
from src.services.ai_generator import generate_ai_content
from src.services.workspace_service import create_google_doc

def create_teaching_package(docs_service, drive_service, topic_or_instructions: str) -> dict:
    """
    Generates a 3-in-1 formatted Teaching & Lecture Google Document:
    1. Lecture Outline & Key Concepts
    2. 5 Practical Student Assignment Questions & Marking Criteria
    3. Answer Key & Solution Code Snippets
    """
    prompt = f"""
You are an expert Computer Science Professor and AI Curriculum Specialist drafting a comprehensive teaching package for Muhammad Hamza.

Topic / Lesson Instructions: "{topic_or_instructions}"

Draft a high-quality 3-in-1 Academic & Teaching Document:

# LECTURE OUTLINE & KEY CONCEPTS
- Executive Summary & Learning Objectives
- Core Theoretical & Practical Concepts (with code examples)
- Real-World Industry Use Cases

# STUDENT ASSIGNMENT & PRACTICAL EXERCISES
- 5 Carefully Structured Practical Questions (ranging from beginner to advanced)
- Clear Submission Requirements & Marking Criteria

# OFFICIAL ANSWER KEY & REFERENCE SOLUTIONS
- Complete, bug-free Reference Code Solutions for all 5 questions
- Explanation of key implementation details

Format cleanly with clear headers (#, ##), bullet points, and code blocks.
"""
    doc_text = generate_ai_content(prompt)
    doc_title = f"Teaching Package: {topic_or_instructions[:35]}"
    
    return create_google_doc(docs_service, drive_service, title=doc_title, content_text=doc_text)
