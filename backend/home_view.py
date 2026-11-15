"""Everything the home page needs for one request: tab, distance, Near me, program filter, shared course."""

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from datetime import datetime, timezone

from courses import TABS, select_courses, with_titles
from state import STATE

DISTANCES = (10, 25, 50, 100, 200)
NOTICES = ("reminder_confirmed", "reminder_cancelled", "reminder_invalid")


def months_needed() -> int:
    return max(c["monthsAhead"] for c in STATE.config.cities.values())


async def courses_for(locale: str) -> list | None:
    """Cached English feed, with titles from the visitor's language feed when there is one."""
    courses, _ = await STATE.feeds["en"].get(months_needed())
    if courses is None or locale == "en" or locale not in STATE.feeds:
        return courses
    translated, _ = await STATE.feeds[locale].get(months_needed())
    return with_titles(courses, translated)


def distance_options(city: dict) -> list:
    return sorted(set(DISTANCES) | {city["radiusKm"]})


def _valid_km(value, city) -> float | None:
    try:
        km = float(value)
    except (TypeError, ValueError):
        return None
    return km if km in distance_options(city) else None


def _norm(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(plain.casefold().replace(",", " ").split())


@lru_cache(maxsize=1)
def _place_index() -> tuple[dict, dict]:
    by_label, by_name = {}, {}
    for p in STATE.places:  # most populous first, so a bare name picks the biggest match
        by_label.setdefault(_norm(p["label"]), p)
        by_name.setdefault(_norm(p["name"]), p)
    return by_label, by_name


def find_place(text: str) -> dict | None:
    """"Kitchener, ON", "kitchener" or "Montreal" -> the place entry, else None."""
    by_label, by_name = _place_index()
    key = _norm(text)
    return by_label.get(key) or by_name.get(key)


def home_area(city: dict, km: float) -> dict:
    return {"latitude": city.get("latitude"), "longitude": city.get("longitude"),
            "radiusKm": km, "monthsAhead": city["monthsAhead"]}


@dataclass
class HomeView:
    city: dict
    texts: dict
    locale: str
    tab: str = "newcomer"
    km: float = 50
    place: str | None = None  # chosen place label, when it is not the site's own city
    place_failed: str | None = None  # text the visitor typed that matched no place
    program: str | None = None
    open_id: str | None = None
    course_missing: bool = False
    notice: str | None = None
    failed: bool = False
    rows: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    programs: list = field(default_factory=list)  # [(slug, name, count)] for the current tab
    cookies: dict = field(default_factory=dict)  # cookie name -> (value, max_age or None)
    shared: dict | None = None  # the shared course, for link previews


async def build_view(city: dict, params, cookies, ip: str, locale: str, texts: dict) -> HomeView:
    view = HomeView(city=city, texts=texts, locale=locale)
    view.tab = params.get("tab") if params.get("tab") in TABS else TABS[0]
    chosen = _valid_km(params.get("km"), city)
    view.km = chosen or _valid_km(cookies.get("km"), city) or city["radiusKm"]
    if chosen:
        view.cookies["km"] = (f"{chosen:g}", 365 * 86400)
    view.notice = params.get("notice") if params.get("notice") in NOTICES else None

    area = home_area(city, view.km)
    place_param = params.get("place")
    text = (place_param if place_param is not None else cookies.get("place") or "").strip()[:80]
    if text and _norm(text) != _norm(city["displayName"]):
        found = find_place(text)
        if found and _norm(found["name"]) == _norm(city["displayName"]):
            found = None  # e.g. "Ottawa, ON" on the Ottawa site: use the site's own centre
        elif found:
            area.update(latitude=found["latitude"], longitude=found["longitude"])
            view.place = found["label"]
        elif place_param is not None:
            view.place_failed = text
    if place_param is not None:
        view.cookies["place"] = (view.place or "", 365 * 86400)

    courses = await courses_for(locale)
    view.failed = courses is None
    now = datetime.now(timezone.utc)
    by_tab = {t: select_courses(courses or [], area, t, now) for t in TABS}
    view.counts = {t: len(rows) for t, rows in by_tab.items()}

    if params.get("course"):
        hit = next(((t, r) for t in TABS for r in by_tab[t] if r["course"]["id"] == params["course"]), None)
        if not hit and view.place:  # shared from this site but the visitor picked another city: use the site's area
            by_tab = {t: select_courses(courses or [], home_area(city, view.km), t, now) for t in TABS}
            hit = next(((t, r) for t in TABS for r in by_tab[t] if r["course"]["id"] == params["course"]), None)
            if hit:
                view.place = None
                view.counts = {t: len(rows) for t, rows in by_tab.items()}
        if hit:
            view.tab, view.open_id, view.shared = hit[0], params["course"], hit[1]["course"]
        else:
            view.course_missing = True

    rows = by_tab[view.tab]
    counts: dict = {}
    for r in rows:
        counts[r["course"]["slug"]] = counts.get(r["course"]["slug"], 0) + 1
    view.programs = [(p["slug"], p["names"].get(locale, p["name"]), counts[p["slug"]]) for p in STATE.programs if p["slug"] in counts]
    program = params.get("program")
    view.program = program if not view.open_id and program in counts else None
    view.rows = [r for r in rows if not view.program or r["course"]["slug"] == view.program]
    return view
