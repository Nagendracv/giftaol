"""Rev 3 + Visit Insights integration tests against the public preview URL (and localhost:8001 with Host headers)."""
import re
import time
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = FE_ENV["REACT_APP_BACKEND_URL"].rstrip("/")
HOST = BASE_URL.split("://", 1)[1]
INTERNAL = "http://localhost:8001"
_BE = dotenv_values("/app/backend/.env")
CRON_SECRET = _BE.get("WEBHOOK_CRON_SECRET")
_SECRET = _BE.get("CLERK_SECRET_KEY")
CLERK = "https://api.clerk.com/v1"
ADMIN_ID = "user_3M7KxnjwE4wv1ipT9ol45VvhSRZ"
MEMBER_ID = "user_3M7KxqOlOVbqlOF5dzQWVHZdQzC"
RECIPIENT = "delivered@resend.dev"


def clerk_token(user_id):
    h = {"Authorization": f"Bearer {_SECRET}", "User-Agent": "emergent-test", "Content-Type": "application/json"}
    s = requests.post(f"{CLERK}/sessions", json={"user_id": user_id}, headers=h, timeout=20)
    s.raise_for_status()
    t = requests.post(f"{CLERK}/sessions/{s.json()['id']}/tokens", json={"expires_in_seconds": 3600}, headers=h, timeout=20)
    t.raise_for_status()
    return t.json()["jwt"]


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(_BE["MONGO_URL"])
    yield c[_BE["DB_NAME"]]
    c.close()


def ids(html):
    return re.findall(r'data-course="([^"]+)"', html)


def get(path, **kw):
    return requests.get(f"{BASE_URL}{path}", timeout=30, **kw)


# Header / footer / cookie notice / title
class TestLayout:
    def test_header_footer_title(self):
        html = get("/").text
        assert "<title>Art of Living Ottawa</title>" in html
        assert re.search(r'data-testid="header-site-name"[^>]*>Art of Living Ottawa<', html)
        for tid in ("site-footer", "footer-privacy-link", "footer-terms-link", "footer-geonames-credit", "cookie-notice"):
            assert f'data-testid="{tid}"' in html, tid
        assert f"© {datetime.now().year}" in html

    def test_cookie_ok_hides_notice(self):
        html = get("/", cookies={"cookie_ok": "1"}).text
        assert 'data-testid="cookie-notice"' not in html

    def test_french_header(self):
        html = get("/", cookies={"lang": "fr"}).text
        assert "Art de vivre Ottawa" in html
        assert "<title>Art de vivre Ottawa</title>" in html

    @pytest.mark.parametrize("path", ["/privacy", "/terms"])
    def test_legal_pages(self, path):
        for lang in ("en", "fr"):
            r = get(path, cookies={"lang": lang})
            assert r.status_code == 200
            assert "Ottawa" in r.text and 'data-testid="site-footer"' in r.text


# Distance
class TestDistance:
    def test_default_50(self):
        html = get("/").text
        opts = re.findall(r'<option value="(\d+)"( selected)?>', html.split('data-testid="distance-select"')[1].split("</select>")[0])
        assert [o[0] for o in opts] == ["10", "25", "50", "100", "200"]
        assert [o[0] for o in opts if o[1]] == ["50"]

    def test_km_200_and_cookie(self):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/?km=200", timeout=30)
        assert "200 km" in re.search(r'data-testid="courses-subheading">([^<]*)<', r.text).group(1)
        assert s.cookies.get("km") == "200"
        r2 = s.get(f"{BASE_URL}/", timeout=30)
        assert '<option value="200" selected>' in r2.text
        c50 = int(re.search(r'tab-count-newcomer">(\d+)<', get("/?km=50").text).group(1))
        c200 = int(re.search(r'tab-count-newcomer">(\d+)<', r.text).group(1))
        assert c200 >= c50

    def test_km_invalid(self):
        assert '<option value="50" selected>' in get("/?km=abc").text
        assert '<option value="50" selected>' in get("/?km=37").text


# City picker
class TestCityPicker:
    def test_chosen_city(self):
        r = requests.get(f"{INTERNAL}/?place=Kitchener", headers={"Host": HOST}, timeout=30)
        assert "Courses near Kitchener, ON" in r.text

    def test_unknown_city(self):
        r = requests.get(f"{INTERNAL}/?place=Atlantis", headers={"Host": HOST}, timeout=30)
        assert 'data-testid="notice-place_not_found"' in r.text and "Courses in and around Ottawa" in r.text


# Program filter
class TestProgram:
    def test_filter(self):
        html = get("/").text
        slugs = re.findall(r'<option value="([a-z0-9-]+)">[^<]*\((\d+)\)</option>',
                           html.split('data-testid="program-filter-select"')[1].split("</select>")[0])
        assert slugs, "no programs"
        slug, n = slugs[0]
        f = get(f"/?program={slug}").text
        assert len(ids(f)) == int(n)
        assert f'<option value="{slug}" selected>' in f
        assert len(ids(get("/?program=bogus").text)) == len(ids(html))


# Calendar + share + shared link
class TestCourseActions:
    def test_ics(self):
        cid = ids(get("/").text)[0]
        r = get(f"/api/courses/{cid}/calendar.ics")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
        assert r.text.count("BEGIN:VEVENT") >= 1 and "END:VCALENDAR" in r.text
        assert get("/api/courses/999999/calendar.ics").status_code == 404

    def test_google_and_share(self):
        html = get("/").text
        cid = ids(html)[0]
        assert re.search(rf'href="https://calendar\.google\.com[^"]*"[^>]*data-testid="course-calendar-google-{cid}"', html)
        assert f'data-testid="course-share-button-{cid}"' in html

    def test_shared_advanced(self):
        adv = ids(get("/?tab=advanced").text)
        if not adv:
            pytest.skip("no advanced courses")
        html = get(f"/?course={adv[0]}").text
        assert 'aria-current="page" data-testid="tab-advanced"' in html
        assert re.search(rf'data-course="{adv[0]}" open', html)
        assert 'property="og:title"' in html

    def test_missing_course(self):
        assert 'data-testid="notice-course_missing"' in get("/?course=999999").text


# Reminders (real email, delivered@resend.dev only)
class TestReminders:
    def test_bad_email(self):
        cid = ids(get("/").text)[0]
        r = requests.post(f"{BASE_URL}/api/reminders", json={"courseId": cid, "email": "nope"}, timeout=30)
        assert r.status_code == 400 and r.json()["message"]

    def test_full_flow(self, mdb):
        cid = ids(get("/").text)[0]
        mdb.reminders.delete_many({"email": RECIPIENT, "course_id": cid})
        r = requests.post(f"{BASE_URL}/api/reminders", json={"courseId": cid, "email": RECIPIENT}, timeout=60)
        assert r.status_code == 200, r.text
        assert "inbox" in r.json()["message"].lower()
        doc = mdb.reminders.find_one({"email": RECIPIENT, "course_id": cid})
        assert doc and doc["status"] == "pending"
        page = get(f"/api/reminders/confirm?token={doc['token']}", allow_redirects=False)
        assert page.status_code == 200 and 'data-testid="reminder-confirm-button"' in page.text  # GET only shows the page
        assert mdb.reminders.find_one({"id": doc["id"]})["status"] == "pending"
        c = requests.post(f"{BASE_URL}/api/reminders/confirm", data={"token": doc["token"]}, allow_redirects=False, timeout=30)
        assert c.status_code == 303 and "notice=reminder_confirmed" in c.headers["location"]
        assert 'data-testid="notice-reminder_confirmed"' in get(c.headers["location"]).text
        assert mdb.reminders.find_one({"id": doc["id"]})["status"] == "confirmed"
        # cron with wrong secret
        assert requests.post(f"{BASE_URL}/api/cron/hourly", headers={"Authorization": "Bearer wrong"}, timeout=30).status_code == 401
        mdb.reminders.update_one({"id": doc["id"]}, {"$set": {"remind_at": datetime.now(timezone.utc) - timedelta(minutes=5)}})
        cr = requests.post(f"{BASE_URL}/api/cron/hourly", headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=30)
        assert cr.status_code == 200 and cr.json()["status"] == "accepted"
        for _ in range(20):
            if not mdb.reminders.find_one({"id": doc["id"]}):
                break
            time.sleep(1)
        assert not mdb.reminders.find_one({"id": doc["id"]}), "reminder not deleted after cron"
        log = subprocess.run("tail -n 300 /var/log/supervisor/backend.err.log", shell=True, capture_output=True, text=True).stdout
        assert "Sent 1 course reminder(s)" in log

    def test_cancel(self, mdb):
        # Insert directly (no email) to test cancel redirect
        tok = "TEST_tok_" + str(time.time())
        mdb.reminders.insert_one({"id": tok, "token": tok, "email": "test_cancel@example.com", "course_id": "x", "status": "pending",
                                  "start": datetime.now(timezone.utc) + timedelta(days=5)})
        c = get(f"/api/reminders/cancel?token={tok}", allow_redirects=False)
        assert c.status_code == 303 and "notice=reminder_cancelled" in c.headers["location"]
        assert 'data-testid="notice-reminder_cancelled"' in get(c.headers["location"]).text
        assert not mdb.reminders.find_one({"token": tok})
        assert "reminder_invalid" in get(f"/api/reminders/cancel?token={tok}", allow_redirects=False).headers["location"]


# Insights
class TestInsights:
    def test_beacon_and_admin(self):
        cid = ids(get("/").text)[0]
        r = requests.post(f"{BASE_URL}/api/insights/event", data='{"kind":"course_open","courseId":"%s"}' % cid,
                          headers={"Content-Type": "text/plain"}, timeout=30)
        assert r.status_code == 204
        admin = {"Authorization": f"Bearer {clerk_token(ADMIN_ID)}"}
        d = get("/api/admin/insights?city=ottawa&days=7", headers=admin).json()
        assert d["days"] == 7 and any(t["tab"] == "newcomer" for t in d["tabs"])
        row = next(c for c in d["courses"] if c["courseId"] == cid)
        assert row["course_open"] >= 1 and row["cityId"] == "ottawa"

    def test_member_and_anon(self):
        assert get("/api/admin/insights").status_code == 401
        member = {"Authorization": f"Bearer {clerk_token(MEMBER_ID)}"}
        assert get("/api/admin/insights", headers=member).status_code == 403


# Regression
class TestRegression:
    def test_unknown_host(self):
        assert requests.get(f"{INTERNAL}/", headers={"Host": "nope.example.com"}, timeout=30).status_code == 404

    def test_healthz(self):
        assert get("/healthz").json() == {"status": "ok"}
        assert get("/api/healthz").json() == {"status": "ok"}
