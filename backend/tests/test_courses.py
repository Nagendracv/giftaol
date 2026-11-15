import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import courses  # noqa: E402
from course_pages import render_courses  # noqa: E402
from courses import CourseFeed, add_months, haversine_km, load_programs, normalize, select_courses  # noqa: E402
from i18n import Texts  # noqa: E402

PROGRAMS = load_programs(json.loads((BACKEND / "config/programs.json").read_text()))
NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
OTTAWA = {"cityId": "ottawa", "displayName": "Ottawa", "timezone": "America/Toronto",
          "latitude": 45.4215, "longitude": -75.6972, "radiusKm": 50, "monthsAhead": 2}


def raw(id, mctype, start, lon, lat, online=0, **extra):
    return {"id": id, "mctype": str(mctype), "title": f"Course {id}", "start_date": start, "end_date": start,
            "coordinates": [lon, lat], "is_online_event": online, "city": "Somewhere",
            "register_url": "https://enroll.artofliving.org/x", "course_fee": 395, "currency": "CAD", **extra}


GATINEAU = (-75.70, 45.48)
TORONTO = (-79.38, 43.65)
SAMPLE = [
    raw(1, 1, "2026-11-20 23:00:00", *GATINEAU),               # newcomer, near
    raw(2, 1, "2026-11-18 23:00:00", *TORONTO),                # newcomer, far
    raw(3, 2, "2026-12-01 23:00:00", -75.69, 45.42),           # advanced, near
    raw(4, 1, "2027-02-01 23:00:00", -75.69, 45.42),           # beyond 2 months
    raw(5, 1, "2026-11-10 23:00:00", -75.69, 45.42),           # already started
    raw(6, 1301, "2026-11-25 23:00:00", *TORONTO, online=1),   # online, far organiser
    raw(7, 1303, "2026-11-30 23:00:00", *GATINEAU, online=1),  # online, near organiser
    raw(8, 999, "2026-11-20 23:00:00", -75.69, 45.42),         # unlisted program type
]


def ids(rows):
    return [r["course"]["id"] for r in rows]


@pytest.fixture
def items():
    return [c for c in (normalize(x, PROGRAMS) for x in SAMPLE) if c]


def test_programs_map_categories():
    assert PROGRAMS["1301"] == {"category": "newcomer", "program": "Art of Living Part 1", "slug": "part-1"}
    assert PROGRAMS["1502"]["category"] == "advanced"
    assert "999" not in PROGRAMS


def test_unlisted_types_dropped(items):
    assert "8" not in [c["id"] for c in items]


def test_newcomer_within_radius_and_window(items):
    assert ids(select_courses(items, OTTAWA, "newcomer", NOW)) == ["1"]


def test_advanced_tab(items):
    assert ids(select_courses(items, OTTAWA, "advanced", NOW)) == ["3"]


def test_online_near_organisers_first(items):
    rows = select_courses(items, OTTAWA, "online", NOW)
    assert ids(rows) == ["7", "6"] and rows[0]["near"] and not rows[1]["near"]


def test_radius_and_months_are_per_city(items):
    wide = {**OTTAWA, "radiusKm": 500, "monthsAhead": 3}
    assert ids(select_courses(items, wide, "newcomer", NOW)) == ["2", "1", "4"]


def test_add_months_and_distance():
    assert add_months(datetime(2026, 12, 31), 2) == datetime(2027, 2, 28)
    assert 340 < haversine_km(45.4215, -75.6972, 43.65, -79.38) < 360


def test_card_shows_city_time_and_register(items):
    texts = Texts(BACKEND / "locales").bundle("en")
    rows = select_courses(items, OTTAWA, "newcomer", NOW)
    from home_view import HomeView
    view = HomeView(city=OTTAWA, texts=texts, locale="en", km=50, rows=rows, counts={"newcomer": 1, "advanced": 1, "online": 2})
    html = render_courses(view, [10, 25, 50, 100, 200], "https://aolottawa.ca")
    assert "Fri, Nov 20 · 6:00 PM" in html  # 23:00 UTC shown in America/Toronto
    assert 'href="https://enroll.artofliving.org/x"' in html and "$395 CAD" in html


def test_schedule_24h_for_french():
    from course_pages import _schedule_line
    fr = Texts(BACKEND / "locales").bundle("fr")
    assert _schedule_line("Fri : 06:00 PM - 08:30 PM", fr) == "Fri : 18 h 00 - 20 h 30"
    assert _schedule_line("Sat : 12:15 AM", fr) == "Sat : 0 h 15"


def test_feed_caches_and_backs_off(monkeypatch):
    calls = []

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"courses": SAMPLE[:2], "total": 2}

    monkeypatch.setattr(courses.requests, "get", lambda *a, **k: calls.append(k["params"]["offset"]) or Resp())
    feed = CourseFeed("https://example.test/courses", PROGRAMS, ttl_seconds=3600)
    first, failed = asyncio.run(feed.get(2))
    asyncio.run(feed.get(2))
    assert len(first) == 2 and not failed and calls == [1]  # second call is served from cache

    def boom(*a, **k):
        raise courses.requests.ConnectionError("down")

    monkeypatch.setattr(courses.requests, "get", boom)
    stale, failed = asyncio.run(CourseFeed("https://example.test", PROGRAMS, 3600).get(2))
    assert stale is None and failed
