import re
import urllib.parse
from src.config import SENDER_NAME, SENDER_PORTFOLIO

def sanitize_phone_number(raw_phone: str) -> str:
    """
    Cleans and formats a raw phone number string into standard international E.164 digits without leading '+'.
    Supports UK (+44), US (+1), Pakistan (+92), and general international formats.
    """
    if not raw_phone or raw_phone.strip() in ["N/A", "None", ""]:
        return ""

    digits = re.sub(r"\D", "", raw_phone)
    if not digits:
        return ""

    # UK local number format starting with 07 (e.g. 07717137308 -> 447717137308)
    if digits.startswith("07") and len(digits) == 11:
        return "44" + digits[1:]

    # UK local number format starting with 0 (e.g. 01615134800 -> 441615134800)
    if digits.startswith("0") and len(digits) == 11:
        return "44" + digits[1:]

    # US/Canada 10-digit number without country code (e.g. 8327747884 -> 18327747884)
    if len(digits) == 10 and not digits.startswith("1"):
        return "1" + digits

    return digits

def generate_whatsapp_message(business_name: str, location: str = "") -> str:
    """
    Generates a short, conversational, personalized outreach text for WhatsApp instant messaging.
    """
    biz_str = f" {business_name}" if business_name and business_name != "N/A" else ""
    loc_str = f" in {location}" if location and location != "N/A" else ""
    
    text = (
        f"Hi{biz_str} team! I'm {SENDER_NAME}, a Web Developer based{loc_str}. "
        f"I build modern websites and automated 24/7 quote & booking forms for local businesses to increase sales. "
        f"Would you be open to a quick 2-minute visual mockup for your business? "
        f"Portfolio: {SENDER_PORTFOLIO}"
    )
    return text

def generate_whatsapp_link(raw_phone: str, business_name: str, location: str = "") -> str:
    """
    Generates a 100% free pre-filled click-to-chat WhatsApp action link (https://wa.me/PHONE?text=MESSAGE).
    Returns 'N/A' if no valid phone number is present.
    """
    clean_phone = sanitize_phone_number(raw_phone)
    if not clean_phone or len(clean_phone) < 8:
        return "N/A"

    msg = generate_whatsapp_message(business_name, location)
    encoded_msg = urllib.parse.quote(msg)
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"
