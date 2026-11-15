"""Rev 3: distance, Near me, program filter, shared course, calendar, legal pages, reminders, cron."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import reminders  # noqa: E402
import server  # noqa: E402
from site_config import load_config_file, validate_config  # noqa: E402
from state import STATE  # noqa: E402
from test_courses import PROGRAMS, SAMPLE, normalize  # noqa: E402

HOST = {"Host": "localhost:5623"}
FUTURE = [{**c, "start_date": c["start_date"].replace("2026", "2099", 1), "end_date": c["end_date"].replace("2026", "2099", 1)}
          for c in SAMPLE]


class SampleFeed:
    async def get(self, months):
        return [c for c in (normalize(x, PROGRAMS) for x in SAMPLE) if c], False


async def no_event(*a, **k):
    return None


@pytest.fixture
def client(app_client, monkeypatch):
    from datetime import datetime, timezone
    import home_view
    monkeypatch.setattr(STATE, "config", validate_config(load_config_file(BACKEND / "config/sites.local.json"), {"en", "fr"}))
    monkeypatch.setattr(STATE, "feeds", {"en": SampleFeed(), "fr": SampleFeed()})
    monkeypatch.setattr(server, "record_visit", lambda *a, **k: None)
    monkeypatch.setattr(server, "record_event", no_event)

    class FixedNow(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(home_view, "datetime", FixedNow)
    monkeypatch.setattr(server, "TRUST_PROXY", True)
    app_client.cookies.clear()
    yield app_client


def test_header_footer_and_cookie_notice(client):
    html = client.get("/", headers=HOST).text
    assert 'header-site-name">Art of Living Ottawa' in html and "<title>Art of Living Ottawa</title>" in html
    assert 'href="/privacy"' in html and "GeoNames" in html and 'data-testid="cookie-notice"' in html
    client.cookies.set("cookie_ok", "1")
    assert 'data-testid="cookie-notice"' not in client.get("/", headers=HOST).text


def test_distance_choice_is_remembered_and_validated(client):
    r = client.get("/?km=500", headers=HOST)
    assert '<option value="50" selected>' in r.text and "km=" not in r.headers.get("set-cookie", "")
    r = client.get("/?km=200", headers=HOST)
    assert "km=200" in r.headers["set-cookie"] and "within 200 km" in r.text
    client.cookies.set("km", "200")
    assert '<option value="200" selected>' in client.get("/", headers=HOST).text


def test_city_picker_centres_the_search_and_is_remembered(client):
    r = client.get("/?place=toronto", headers=HOST)
    assert "Courses near Toronto, ON" in r.text and 'tab-count-newcomer">1<' in r.text and "place=" in r.headers["set-cookie"]
    assert 'value="Toronto, ON"' in r.text and '<option value="Kitchener, ON">' in r.text
    client.cookies.set("place", "Toronto, ON")
    assert "Courses near Toronto, ON" in client.get("/", headers=HOST).text
    client.cookies.clear()
    assert "Courses near Montréal, QC" in client.get("/?place=Montreal", headers=HOST).text  # accents optional


def test_shared_course_opens_even_with_another_city_chosen(client):
    client.cookies.set("place", "Toronto, ON")
    html = client.get("/?course=3", headers=HOST).text
    assert "open data-focus" in html and "Courses in and around Ottawa" in html
    client.cookies.clear()


def test_own_city_from_list_and_no_comma(client):
    assert "Courses in and around Ottawa" in client.get("/?place=Ottawa, ON", headers=HOST).text
    assert "Courses near Kitchener, ON" in client.get("/?place=kitchener on", headers=HOST).text


def test_unknown_or_own_city_falls_back(client):
    html = client.get("/?place=Atlantis", headers=HOST).text
    assert "Courses in and around Ottawa" in html and "notice-place_not_found" in html
    html = client.get("/?place=Ottawa", headers=HOST).text
    assert "Courses in and around Ottawa" in html and "notice-place_not_found" not in html


def test_program_filter(client):
    html = client.get("/?tab=online&program=sahaj", headers=HOST).text
    assert 'value="sahaj" selected' in html and "course-card-7" in html and "course-card-6" not in html
    assert "course-card-6" in client.get("/?tab=online&program=unknown", headers=HOST).text


def test_shared_course_opens_on_its_tab(client):
    html = client.get("/?course=3", headers=HOST).text
    assert 'aria-current="page" data-testid="tab-advanced"' in html and "open data-focus" in html
    assert 'property="og:title" content="Course 3"' in html
    assert "notice-course_missing" in client.get("/?course=2", headers=HOST).text  # outside this site's area


def test_calendar_file_has_course_details(client):
    r = client.get("/api/courses/1/calendar.ics", headers=HOST)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VEVENT" in r.text and "SUMMARY:Course 1" in r.text and "DTSTART:20261120T230000Z" in r.text


def test_legal_pages_in_both_languages(client):
    assert "Art of Living Ottawa respects your privacy" in client.get("/privacy", headers=HOST).text
    client.cookies.set("lang", "fr")
    assert "Art de vivre Ottawa" in client.get("/terms", headers=HOST).text


def test_reminder_validation_and_confirmation_email(client, monkeypatch):
    sent = []

    async def fake_send(**kwargs):
        sent.append(kwargs)
    monkeypatch.setattr(reminders, "send_email", fake_send)
    monkeypatch.setattr(reminders, "record_course_event", no_event)
    feed = type("F", (), {"get": lambda self, m: _future()})()
    monkeypatch.setattr(STATE, "feeds", {"en": feed, "fr": feed})
    bad = client.post("/api/reminders", headers=HOST, json={"courseId": "1", "email": "nope"})
    assert bad.status_code == 400
    ok = client.post("/api/reminders", headers=HOST, json={"courseId": "1", "email": "test+rev3@example.com"})
    assert ok.status_code == 200 and sent and sent[0]["from_name"] == "Art of Living Ottawa"
    assert "/api/reminders/confirm?token=" in sent[0]["html"]
    from pymongo import MongoClient
    MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].reminders.delete_many({"email": "test+rev3@example.com"})


async def _future():
    return [c for c in (normalize(x, PROGRAMS) for x in FUTURE) if c], False


def test_cron_requires_secret(client):
    assert client.post("/api/cron/hourly", headers={"Authorization": "Bearer wrong"}).status_code == 401
