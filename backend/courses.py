"""Courses from the shared Unity API: one cached Canada-wide pull, filtered per city."""

import asyncio
import calendar
import logging
import math
import re
import time
from datetime import datetime, timedelta, timezone
from html import unescape

import requests
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("citysites")
PAGE_SIZE = 100
MAX_PAGES = 30
RETRY_AFTER_FAILURE = 120  # seconds; never hammer the shared API when it is down
TABS = ("newcomer", "advanced", "online")
TAG_RE = re.compile(r"<[^>]+>")


def program_list(raw: dict) -> list[dict]:
    """Programs in display order: [{"slug", "name", "category"}]."""
    return [{"slug": p["slug"], "name": p["name"], "names": p.get("names", {}), "category": c}
            for c in ("newcomer", "advanced") for p in raw[c]]


def load_programs(raw: dict) -> dict[str, dict]:
    """mctype -> {"category": "newcomer"|"advanced", "program": name}."""
    out = {}
    for category in ("newcomer", "advanced"):
        for program in raw[category]:
            for mctype in program["mctypes"]:
                out[str(mctype)] = {"category": category, "program": program["name"], "slug": program["slug"]}
    return out


def add_months(dt: datetime, months: int) -> datetime:
    index = dt.month - 1 + months
    year, month = dt.year + index // 12, index % 12 + 1
    return dt.replace(year=year, month=month, day=min(dt.day, calendar.monthrange(year, month)[1]))


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def _utc(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _fee(value):
    return value if isinstance(value, (int, float)) and value > 0 else None


def _clean(text) -> str:
    return TAG_RE.sub("", unescape(text or "")).replace("\u202f", " ").strip()


def normalize(raw: dict, programs: dict) -> dict | None:
    info = programs.get(str(raw.get("mctype")))
    start = _utc(raw.get("start_date"))
    if not info or not start:
        return None
    coords = raw.get("coordinates") or []
    lon, lat = (coords[0], coords[1]) if len(coords) >= 2 else (None, None)
    timings = [_clean(t) for t in (raw.get("course_complex_timing") or "").split("<br/>")]
    end = _utc(raw.get("end_date")) or start
    sessions = sorted(
        (datetime.fromtimestamp(s["start_time"], timezone.utc), datetime.fromtimestamp(s["end_time"], timezone.utc))
        for s in raw.get("bx_course_timings") or []
        if isinstance(s.get("start_time"), int) and isinstance(s.get("end_time"), int) and s["end_time"] > s["start_time"])
    return {
        "id": str(raw.get("id")),
        "title": _clean(raw.get("title")) or info["program"],
        "program": info["program"],
        "category": info["category"],
        "slug": info["slug"],
        "sessions": sessions or [(start, max(end, start))],
        "online": bool(raw.get("is_online_event")),
        "start": start,
        "end": end,
        "timings": [t for t in timings if t],
        "address": _clean(raw.get("address_short") or raw.get("address")),
        "city": _clean(raw.get("city")).strip(" -"),
        "lat": lat,
        "lon": lon,
        "teachers": [t for t in raw.get("teachers") or [] if t],
        "currency": raw.get("currency") or "",
        "fees": {k: _fee(raw.get(src)) for k, src in
                 (("fee", "course_fee"), ("studentFee", "student_fee"), ("repeaterFee", "repeater_fee"), ("seniorFee", "senior_fee"))},
        "languages": raw.get("course_language") or [],
        "registerUrl": raw.get("register_url") or "",
        "closed": bool(raw.get("is_registration_closed")),
        "full": bool(raw.get("is_event_capacity_full")),
        "contactName": _clean(raw.get("contact_name")),
        "contactEmail": raw.get("email") or "",
        "phones": [p for p in raw.get("phones") or [] if p],
    }


def select_courses(courses: list, area: dict, tab: str, now: datetime) -> list[dict]:
    """Courses for one tab around an area (latitude, longitude, radiusKm, monthsAhead): [{"course", "distanceKm", "near"}]."""
    end = add_months(now, area["monthsAhead"])
    lat, lon, radius = area.get("latitude"), area.get("longitude"), area["radiusKm"]
    rows = []
    for c in courses:
        if not now <= c["start"] <= end:
            continue
        distance = haversine_km(lat, lon, c["lat"], c["lon"]) if lat is not None and c["lat"] is not None else None
        near = distance is not None and distance <= radius
        if tab == "online" and c["online"]:
            rows.append({"course": c, "distanceKm": distance, "near": near})
        elif tab != "online" and not c["online"] and c["category"] == tab and near:
            rows.append({"course": c, "distanceKm": distance, "near": near})
    if tab == "online":
        return sorted(rows, key=lambda r: (not r["near"], r["course"]["start"]))
    return sorted(rows, key=lambda r: r["course"]["start"])


class CourseFeed:
    """Fetch on first use, keep for `ttl_seconds`; one fetch at a time; serve stale data on failure."""

    def __init__(self, base_url: str, programs: dict, ttl_seconds: int, language: str = "en-ca"):
        self.base_url, self.programs, self.ttl, self.language = base_url, programs, ttl_seconds, language
        self._courses = None
        self._months = 0
        self._fetched_at = 0.0
        self._failed_at = 0.0
        self._lock = asyncio.Lock()

    def _fetch(self, months: int) -> list:
        horizon = add_months(datetime.now(timezone.utc), months) + timedelta(days=1)
        mctypes = ",".join(self.programs)
        items, page = [], 0
        for page in range(1, MAX_PAGES + 1):
            resp = requests.get(self.base_url, params={"offset": page, "language": self.language, "mctypes": mctypes, "mctype": mctypes},
                                headers={"User-Agent": "aol-city-sites/1.0"}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("courses") or []
            items.extend(batch)
            last = _utc(batch[-1].get("start_date")) if batch else None
            if len(batch) < PAGE_SIZE or len(items) >= int(data.get("total") or 0) or (last and last > horizon):
                break
        logger.info("Fetched %d %s courses from the Unity API in %d page(s)", len(items), self.language, page)
        return [c for c in (normalize(x, self.programs) for x in items) if c]

    async def get(self, months: int) -> tuple[list | None, bool]:
        """Return (courses, failed). `months` is the longest window any city needs."""
        async with self._lock:
            now = time.monotonic()
            if self._courses is not None and now - self._fetched_at < self.ttl and months <= self._months:
                return self._courses, False
            if now - self._failed_at < RETRY_AFTER_FAILURE:
                return self._courses, True
            try:
                courses = await run_in_threadpool(self._fetch, months)
            except Exception as exc:
                self._failed_at = time.monotonic()
                logger.error("Unity courses API request failed: %s", exc)
                return self._courses, True
            self._courses, self._months, self._fetched_at = courses, months, time.monotonic()
            return courses, False


def tab_of(course: dict) -> str:
    return "online" if course["online"] else course["category"]


def find_course(courses: list | None, course_id: str) -> dict | None:
    return next((c for c in courses or [] if c["id"] == course_id), None)


def with_titles(courses: list, translated: list | None) -> list:
    """Overlay titles from another language's feed (matched by course id); keep the original when missing."""
    titles = {c["id"]: c["title"] for c in translated or []}
    return [{**c, "title": titles.get(c["id"]) or c["title"]} for c in courses]
