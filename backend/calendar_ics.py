"""Add-to-calendar: .ics files (one event per session) and a Google Calendar link."""

from datetime import datetime, timezone
from urllib.parse import urlencode


def _stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545 lines are at most 75 octets; continue with a leading space."""
    out, raw = [], line.encode("utf-8")
    while len(raw) > 75:
        cut = 75
        while (raw[cut] & 0xC0) == 0x80:  # don't split a UTF-8 character
            cut -= 1
        out.append(raw[:cut].decode("utf-8"))
        raw = b" " + raw[cut:]
    out.append(raw.decode("utf-8"))
    return "\r\n".join(out)


def description(course: dict, page_url: str, texts: dict) -> str:
    lines = [f'{texts["calendarDetails"]}: {page_url}']
    if course["registerUrl"]:
        lines.append(f'{texts["register"]}: {course["registerUrl"]}')
    contact = " · ".join(x for x in [course["contactName"], course["contactEmail"], *course["phones"]] if x)
    if contact:
        lines.append(f'{texts["contact"]}: {contact}')
    return "\n".join(lines)


def location(course: dict, texts: dict) -> str:
    return texts["online"] if course["online"] else course["address"]


def build_ics(course: dict, page_url: str, texts: dict) -> str:
    now = _stamp(datetime.now(timezone.utc))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Art of Living city sites//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    for i, (start, end) in enumerate(course["sessions"], 1):
        lines += ["BEGIN:VEVENT", f'UID:{course["id"]}-{i}@aol-city-sites', f"DTSTAMP:{now}",
                  f"DTSTART:{_stamp(start)}", f"DTEND:{_stamp(end)}",
                  f'SUMMARY:{_esc(course["title"])}', f"LOCATION:{_esc(location(course, texts))}",
                  f"DESCRIPTION:{_esc(description(course, page_url, texts))}", f"URL:{page_url}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def google_link(course: dict, page_url: str, texts: dict) -> str:
    start, end = course["sessions"][0]
    sessions = course["timings"] and "\n" + "\n".join(course["timings"])
    params = {"action": "TEMPLATE", "text": course["title"], "dates": f"{_stamp(start)}/{_stamp(end)}",
              "details": description(course, page_url, texts) + (sessions or ""), "location": location(course, texts)}
    return "https://calendar.google.com/calendar/render?" + urlencode(params)
