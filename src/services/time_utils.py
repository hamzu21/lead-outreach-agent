import datetime
try:
    from zoneinfo import ZoneInfo
    PKT_TZ = ZoneInfo("Asia/Karachi")
except Exception:
    PKT_TZ = datetime.timezone(datetime.timedelta(hours=5))

def get_pkt_now() -> datetime.datetime:
    """
    Returns current datetime object forced to Pakistan Standard Time (PKT / UTC+5).
    """
    return datetime.datetime.now(PKT_TZ)

def get_pkt_now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Returns current PKT timestamp string formatted according to fmt.
    Default format: "YYYY-MM-DD HH:MM:SS"
    """
    return get_pkt_now().strftime(fmt)
