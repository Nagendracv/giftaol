"""Integration tests: course tabs on the city home page (Unity API feed), per-city radius/months config, caching."""
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

from test_citysites_api import BASE_URL, INTERNAL, ADMIN_ID, clerk_token

ERR_LOG = Path("/var/log/supervisor/backend.err.log")
CARD_RE = re.compile(r'data-testid="course-card-(\d+)">.*?<h3 class="cs-name">([^<]*)</h3><p class="cs-meta">([^<]*)</p>'
                     r'(?:<div class="cs-badges">(.*?)</div>)?<span class="cs-chev">', re.S)
NEWCOMER = {"Art of Living Part 1", "Sahaj Samadhi Meditation", "ART Excel", "YES!", "Sri Sri Yoga Program",
            "SKY Happiness Retreat", "Deep Sleep & Anxiety Relief", "IP Junior Program", "IP Kids Program", "IP Teens Program"}


def count(html, tab):
    return int(re.search(rf'data-testid="tab-count-{tab}">(\d+)<', html).group(1))


def cards(html):
    return [{"id": m[0], "title": m[1], "meta": m[2], "badges": re.sub("<[^>]+>", "|", m[3] or "")} for m in CARD_RE.findall(html)]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {clerk_token(ADMIN_ID)}"}


# --- Public: tabs, filtering, details ---
class TestCourseTabs:
    def test_default_newcomer(self):
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200
        t = r.text
        assert 'data-testid="courses-heading">Courses in and around Ottawa<' in t
        assert 'aria-current="page" data-testid="tab-newcomer"' in t
        assert 'aria-current="false" data-testid="tab-advanced"' in t and 'aria-current="false" data-testid="tab-online"' in t
        cs = cards(t)
        assert len(cs) == count(t, "newcomer")
        for c in cs:
            km = int(re.search(r"(\d+) km away", c["badges"]).group(1))
            assert km <= 50 and "Online" not in c["badges"]
            assert any(x in c["meta"] for x in ("Ottawa", "Gatineau", "Kanata", "Stittsville", "Orl", "Nepean")), c

    def test_details_and_register(self):
        t = requests.get(f"{BASE_URL}/").text
        cs = cards(t)
        if not cs:
            pytest.skip("no newcomer courses right now")
        cid = cs[0]["id"]
        body = re.search(rf'data-testid="course-details-{cid}">(.*?)</div></details>', t, re.S).group(1)
        for label in ("Schedule", "Venue", "Language"):
            assert f"<dt>{label}" in body, label
        m = re.search(r'<a class="cs-register" href="([^"]+)" target="_blank" rel="noopener noreferrer"', body)
        assert m and "enroll.artofliving.org" in m.group(1)

    def test_advanced(self):
        t = requests.get(f"{BASE_URL}/?tab=advanced").text
        assert 'aria-current="page" data-testid="tab-advanced"' in t
        for c in cards(t):
            assert c["title"] not in NEWCOMER

    def test_online_near_first(self):
        t = requests.get(f"{BASE_URL}/?tab=online").text
        cs = cards(t)
        assert len(cs) == count(t, "online") and cs
        near = [("Organiser near Ottawa" in c["badges"]) for c in cs]
        assert near == sorted(near, reverse=True), "near organisers must come first"
        assert all("Online" in c["badges"] for c in cs)

    def test_bad_tab_falls_back(self):
        t = requests.get(f"{BASE_URL}/?tab=zzz").text
        assert 'aria-current="page" data-testid="tab-newcomer"' in t

    def test_lang_keeps_tab_and_french(self):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/?lang=fr&tab=online", allow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/?tab=online"
        t = s.get(f"{BASE_URL}/?tab=online").text
        for w in ("Cours d&#x27;initiation", "Cours avancés", "Cours en ligne", "Cours à Ottawa"):
            assert w in t or w.replace("&#x27;", "'") in t, w
        cs = cards(t)
        assert cs and re.search(r"(lun|mar|mer|jeu|ven|sam|dim)\. \d+ \w+", cs[0]["meta"]) and re.search(r"\d+ h \d\d", cs[0]["meta"])
        s.get(f"{BASE_URL}/?lang=en")

    def test_home_content_api(self):
        r = requests.get(f"{BASE_URL}/api/home-content?tab=online")
        assert r.status_code == 200
        d = r.json()
        assert 'data-testid="tab-panel-online"' in d["html"] and ".cs-card" in d["css"]
        r = requests.get(f"{INTERNAL}/api/home-content", headers={"Host": "unknown.example"})
        assert r.status_code == 404

    def test_cache_no_refetch(self):
        size = ERR_LOG.stat().st_size
        for _ in range(3):
            requests.get(f"{BASE_URL}/")
        time.sleep(0.5)
        assert "Fetched" not in ERR_LOG.read_bytes()[size:].decode(errors="ignore")


# --- Admin: per-city radius/months ---
class TestCityArea:
    def test_radius_months_and_validation(self, admin_h):
        base = requests.get(f"{BASE_URL}/").text
        cfg = requests.get(f"{BASE_URL}/api/admin/config", headers=admin_h).json()["config"]
        try:
            for c in cfg["cities"]:
                if c["cityId"] == "ottawa":
                    c["radiusKm"], c["monthsAhead"] = 200, 3
            size = ERR_LOG.stat().st_size
            r = requests.put(f"{BASE_URL}/api/admin/config", json=cfg, headers=admin_h)
            assert r.status_code == 200, r.text
            t = requests.get(f"{BASE_URL}/").text
            requests.get(f"{BASE_URL}/?tab=online")
            assert "within 200 km" in t and "next 3 months" in t
            assert count(t, "newcomer") >= count(base, "newcomer")
            time.sleep(0.5)
            assert ERR_LOG.read_bytes()[size:].decode(errors="ignore").count("Fetched") <= 1
            for key, val in (("radiusKm", 0), ("monthsAhead", 13), ("longitude", None)):
                bad = {**cfg, "cities": [dict(c) for c in cfg["cities"]]}
                ott = next(c for c in bad["cities"] if c["cityId"] == "ottawa")
                if val is None:
                    ott.pop(key)
                else:
                    ott[key] = val
                r = requests.put(f"{BASE_URL}/api/admin/config", json=bad, headers=admin_h)
                assert r.status_code == 422, (key, r.text)
        finally:
            r = requests.delete(f"{BASE_URL}/api/admin/config", headers=admin_h)
            assert r.status_code == 200 and r.json()["source"] == "file"
        assert "within 50 km" in requests.get(f"{BASE_URL}/").text
