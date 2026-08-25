import re

def clean_text_for_doc(text: str) -> str:
    """
    Strips raw markdown syntax (asterisks, hashtags, dashes, raw backticks)
    so Google Docs look clean and professional without raw code markers.
    """
    if not text:
        return ""

    # Remove headers ###, ##, #
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    
    # Remove horizontal rules ---, ***, ___
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Convert **bold** or *italic* to plain clean text
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", text)

    # Convert markdown bullet points (* item or - item) to clean bullet character (• item)
    text = re.sub(r"^\s*[*|-]\s+", "• ", text, flags=re.MULTILINE)

    # Remove backticks ```
    text = text.replace("```json", "").replace("```", "").replace("`", "")

    # Clean multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text_for_telegram(text: str) -> str:
    """
    Converts GitHub/Gemini Markdown to clean Telegram Markdown:
    - Replaces **double asterisks** with *single asterisk* (Telegram Bold)
    - Removes ### headers and converts to *Header*
    - Converts raw list items (* **) to clean bullet points (• *Header:*)
    - Removes horizontal lines (---)
    - Removes orphan/stray asterisks
    """
    if not text:
        return ""

    # 1. Remove horizontal rules (--- or ***)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # 2. Convert markdown headers ### Header to *Header*
    text = re.sub(r"^\s*#{1,6}\s*(.*)$", r"*\1*", text, flags=re.MULTILINE)

    # 3. Clean list bullets: '* **Header:**' -> '• *Header:*'
    text = re.sub(r"^\s*[*|-]\s+\*\*(.*?)\*\*", r"• *\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[*|-]\s+\*(.*?)\*", r"• *\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[*|-]\s+", r"• ", text, flags=re.MULTILINE)

    # 4. Replace remaining double asterisks **bold** with single asterisk *bold*
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)

    # 5. Fix double single asterisks ** that might remain
    text = text.replace("**", "*")

    # 6. Remove stray isolated asterisks surrounded by spaces
    text = re.sub(r"\s+\*\s+", " ", text)
    text = re.sub(r"^\s*\*\s*$", "", text, flags=re.MULTILINE)

    # 7. Clean triple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
