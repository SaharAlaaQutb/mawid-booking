from dataclasses import dataclass
from datetime import UTC, datetime

LINE_LIMIT = 75


@dataclass(frozen=True, slots=True)
class IcsEvent:
    uid: str
    summary: str
    description: str
    starts_at: datetime
    ends_at: datetime
    location: str = ""
    url: str = ""
    dtstamp: datetime | None = None


def build_ics(event: IcsEvent) -> str:
    stamp = event.dtstamp or datetime.now(UTC)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mawid//Appointment//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{_escape(event.uid)}",
        f"DTSTAMP:{_utc(stamp)}",
        f"DTSTART:{_utc(event.starts_at)}",
        f"DTEND:{_utc(event.ends_at)}",
        f"SUMMARY:{_escape(event.summary)}",
        f"DESCRIPTION:{_escape(event.description)}",
    ]
    if event.location:
        lines.append(f"LOCATION:{_escape(event.location)}")
    if event.url:
        lines.append(f"URL:{_escape(event.url)}")
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    if len(line.encode("utf-8")) <= LINE_LIMIT:
        return line
    chunks: list[str] = []
    current = ""
    for character in line:
        limit = LINE_LIMIT if not chunks else LINE_LIMIT - 1
        if len((current + character).encode("utf-8")) > limit:
            chunks.append(current)
            current = character
        else:
            current += character
    chunks.append(current)
    return "\r\n ".join(chunks)
