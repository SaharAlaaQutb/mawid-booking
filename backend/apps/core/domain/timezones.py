from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_valid_timezone(value: str) -> bool:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True
