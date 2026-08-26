import os
import requests
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/")

from src.services.formatting_cleaner import clean_text_for_telegram

def send_telegram_message(text: str, chat_id: str = None, parse_mode: str = "Markdown") -> bool:
    """
    Sends a message to the specified Telegram chat using the Telegram Bot API with clean formatting.
    """
    bot_token = (TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip(' "\'\t\r\n')
    target_chat = (chat_id or TELEGRAM_CHAT_ID or os.getenv("TELEGRAM_CHAT_ID", "")).strip(' "\'\t\r\n')

    if not bot_token or not target_chat:
        print("[Telegram] Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")
        return False

    cleaned_text = clean_text_for_telegram(text)

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": cleaned_text,
        "parse_mode": parse_mode
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        res_data = response.json()
        if not res_data.get("ok"):
            # Fallback to plain text if markdown formatting failed
            if parse_mode:
                payload["parse_mode"] = ""
                response = requests.post(url, json=payload, timeout=15)
                res_data = response.json()
            if not res_data.get("ok"):
                print(f"[Telegram] Failed to send message: {res_data.get('description')}")
                return False
        return True
    except Exception as e:
        print(f"[Telegram] Exception sending message: {e}")
        return False

def get_telegram_updates(offset: int = 0, timeout: int = 10) -> list:
    """
    Fetches unhandled updates (messages, commands) from the Telegram Bot API.
    """
    bot_token = (TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip(' "\'\t\r\n')
    if not bot_token:
        return []

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/getUpdates"
    params = {"offset": offset, "timeout": timeout}

    try:
        response = requests.get(url, params=params, timeout=timeout + 15)
        res_data = response.json()
        if res_data.get("ok"):
            return res_data.get("result", [])
        return []
    except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
        # Long polling timeout is expected when no new messages arrive within the timeout window
        return []
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
        print(f"[Telegram Notice] Connection to {TELEGRAM_API_BASE} timed out or was blocked by local ISP/network firewall.")
        print("💡 Solution: Turn on 1.1.1.1 WARP / VPN on your PC for local testing, OR deploy to Cloud (Render/GitHub Actions) where Telegram is 100% unblocked.")
        return []
    except Exception as e:
        print(f"[Telegram] Error fetching updates: {e}")
        return []

def get_telegram_file_bytes(file_id: str) -> bytes:
    """
    Downloads file content (e.g. photo receipt) from Telegram servers by file_id.
    """
    bot_token = TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        return b""

    try:
        # Get File Path
        file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        res = requests.get(file_info_url, params={"file_id": file_id}, timeout=15)
        file_info = res.json()
        if not file_info.get("ok"):
            return b""
        
        file_path = file_info["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        dl_res = requests.get(download_url, timeout=30)
        return dl_res.content
    except Exception as e:
        print(f"[Telegram] Error downloading file {file_id}: {e}")
        return b""

def download_telegram_file(file_id: str, local_filename: str) -> str:
    """
    Downloads a document/file from Telegram and saves it locally under downloads/.
    """
    file_bytes = get_telegram_file_bytes(file_id)
    if not file_bytes:
        return ""
    
    os.makedirs("downloads", exist_ok=True)
    local_path = os.path.join("downloads", local_filename)
    with open(local_path, "wb") as f:
        f.write(file_bytes)
    return local_path
