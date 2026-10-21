from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Colombo"


def get_local_now(timezone_name: str = DEFAULT_TIMEZONE) -> datetime:
    return datetime.now(ZoneInfo(timezone_name))
