"""Integration tests: host->city resolution, i18n, /api/site, auth, admin config/texts/users/logs."""
import os
import struct
import subprocess
import time
import zlib
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

FE_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = FE_ENV["REACT_APP_BACKEND_URL"].rstrip("/")
INTERNAL = "http://localhost:8001"
_SECRET = dotenv_values("/app/backend/.env").get("CLERK_SECRET_KEY")
CLERK = "https://api.clerk.com/v1"
ADMIN_ID = "user_3M7KxnjwE4wv1ipT9ol45VvhSRZ"
MEMBER_ID = "user_3M7KxqOlOVbqlOF5dzQWVHZdQzC"
ERR_LOG = Path("/var/log/supervisor/backend.err.log")


def clerk_token(user_id):
    h = {"Authorization": f"Bearer {_SECRET}", "User-Agent": "emergent-test", "Content-Type": "application/json"}
    s = requests.post(f"{CLERK}/sessions", json={"user_id": user_id}, headers=h, timeout=20)
    s.raise_for_status()
    t = requests.post(f"{CLERK}/sessions/{s.json()['id']}/tokens", json={"expires_in_seconds": 3600}, headers=h, timeout=20)
    t.raise_for_status()
    return t.json()["jwt"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {clerk_token(ADMIN_ID)}"}


@pytest.fixture(scope="module")
def member_h():
    return {"Authorization": f"Bearer {clerk_token(MEMBER_ID)}"}


def home(host, **kw):
    return requests.get(f"{INTERNAL}/", headers={"Host": host, **kw.pop("headers", {})}, allow_redirects=False, **kw)


def tiny_png():
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    raw = b"\x00\xff\x00\x00"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# --- Public: home page, host resolution, i18n ---
class TestPublic:
    def test_preview_home(self):
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200
        assert 'data-testid="courses-heading">Courses in and around Ottawa<' in r.text
        assert 'city-greeting' not in r.text
        assert "/api/static/aol-logo.png" in r.text
        assert 'data-testid="language-switcher"' in r.text
        assert 'href="/sign-in" data-testid="auth-button"' in r.text

    def test_lang_cookie(self):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/?lang=fr", allow_redirects=False)
        assert r.status_code == 303 and "lang=fr" in r.headers.get("set-cookie", "")
        r = s.get(f"{BASE_URL}/")
        assert "Cours à Ottawa et dans les environs" in r.text
        r = s.get(f"{BASE_URL}/?lang=en")
        assert "Courses in and around Ottawa" in r.text

    @pytest.mark.parametrize("host,city", [("localhost:5624", "mississauga"), ("AOLOTTAWA.CA", "ottawa"),
                                           ("aolottawa.ca:443", "ottawa"), ("localhost:5623", "ottawa"),
                                           ("aolottawa.ca.", "ottawa")])
    def test_host_resolution(self, host, city):
        r = home(host)
        assert r.status_code == 200 and f"Courses in and around {city.capitalize()}" in r.text

    def test_xfh_priority(self):
        r = home("localhost:5623", headers={"X-Forwarded-Host": "localhost:5624"})
        assert "Courses in and around Mississauga" in r.text

    def test_unknown_host(self):
        size = ERR_LOG.stat().st_size
        r = home("unknown.example")
        assert r.status_code == 404 and "This site is not configured" in r.text
        time.sleep(0.5)
        tail = ERR_LOG.read_bytes()[size:].decode(errors="ignore")
        assert "WARNING" in tail and "unknown.example" in tail
        assert "cityId=unknown" in tail

    def test_city_id_logged(self):
        size = ERR_LOG.stat().st_size
        home("localhost:5623")
        time.sleep(0.5)
        assert "cityId=ottawa" in ERR_LOG.read_bytes()[size:].decode(errors="ignore")

    @pytest.mark.parametrize("host", ["unknown.example", "localhost:5624", ""])
    def test_healthz(self, host):
        r = requests.get(f"{INTERNAL}/healthz", headers={"Host": host} if host else {})
        assert r.status_code == 200 and r.json()["status"] == "ok"

    def test_api_site(self):
        d = requests.get(f"{BASE_URL}/api/site").json()
        assert d["configured"] is True and d["city"]["cityId"] == "ottawa"
        assert d["texts"]["coursesHeading"] == "Courses in and around {city}" and "greeting" not in d["city"]
        d = requests.get(f"{INTERNAL}/api/site", headers={"Host": "nowhere.test"}).json()
        assert d["configured"] is False and d["city"] is None


# --- Auth: 401 / 403 ---
class TestAuth:
    @pytest.mark.parametrize("path", ["/api/admin/config", "/api/admin/logs", "/api/admin/texts", "/api/users"])
    def test_no_token(self, path):
        assert requests.get(f"{BASE_URL}{path}").status_code == 401

    @pytest.mark.parametrize("path", ["/api/admin/config", "/api/admin/logs", "/api/admin/texts", "/api/users"])
    def test_member_forbidden(self, path, member_h):
        assert requests.get(f"{BASE_URL}{path}", headers=member_h).status_code == 403

    def test_me(self, admin_h, member_h):
        assert requests.get(f"{BASE_URL}/api/me", headers=admin_h).json()["role"] == "admin"
        assert requests.get(f"{BASE_URL}/api/me", headers=member_h).json()["role"] == "member"


# --- Admin: site config, logo, logs, texts, users ---
class TestAdmin:
    def test_config_edit_validate_reset(self, admin_h):
        cfg = requests.get(f"{BASE_URL}/api/admin/config", headers=admin_h).json()["config"]
        try:
            for c in cfg["cities"]:
                if c["cityId"] == "mississauga":
                    c["displayName"] = "TEST_Missi"
            cfg["cities"].append({"cityId": "testcity", "displayName": "TEST_City", "timezone": "America/Toronto",
                                  "hosts": ["localhost:5699"], "defaultLocale": "en"})
            r = requests.put(f"{BASE_URL}/api/admin/config", json=cfg, headers=admin_h)
            assert r.status_code == 200 and r.json()["source"] == "admin"
            assert "Courses in and around TEST_Missi" in home("localhost:5624").text
            assert "Courses in and around TEST_City" in home("localhost:5699").text
            # duplicate host
            bad = {**cfg, "cities": [dict(c) for c in cfg["cities"]]}
            bad["cities"][-1] = {**bad["cities"][-1], "hosts": ["localhost:5624"]}
            r = requests.put(f"{BASE_URL}/api/admin/config", json=bad, headers=admin_h)
            assert r.status_code == 422 and "localhost:5624" in r.json()["detail"]
            bad["cities"][-1] = {**bad["cities"][-1], "hosts": ["localhost:5699"], "timezone": "Mars/Base"}
            r = requests.put(f"{BASE_URL}/api/admin/config", json=bad, headers=admin_h)
            assert r.status_code == 422 and "timezone" in r.json()["detail"]
            # logo
            r = requests.post(f"{BASE_URL}/api/admin/cities/testcity/logo", headers=admin_h,
                              files={"file": ("l.png", tiny_png(), "image/png")})
            assert r.status_code == 200, r.text
            url = r.json()["logoUrl"]
            assert url in home("localhost:5699").text
            img = requests.get(f"{BASE_URL}{url}")
            assert img.status_code == 200 and img.headers["content-type"] == "image/png" and img.content[:4] == b"\x89PNG"
            r = requests.post(f"{BASE_URL}/api/admin/cities/testcity/logo", headers=admin_h,
                              files={"file": ("l.txt", b"hi", "text/plain")})
            assert r.status_code == 400
        finally:
            r = requests.delete(f"{BASE_URL}/api/admin/config", headers=admin_h)
            assert r.status_code == 200 and r.json()["source"] == "file"
        assert home("localhost:5699").status_code == 404
        assert "Courses in and around Mississauga" in home("localhost:5624").text

    def test_logs(self, admin_h):
        home("localhost:5624")
        time.sleep(1)
        d = requests.get(f"{BASE_URL}/api/admin/logs", params={"city": "mississauga", "size": 5}, headers=admin_h).json()
        assert d["total"] >= 1 and all(i["city_id"] == "mississauga" for i in d["items"])
        assert {"ts", "ip", "host", "path", "city_id", "status"} <= set(d["items"][0])
        d = requests.get(f"{BASE_URL}/api/admin/logs", params={"host": "5624"}, headers=admin_h).json()
        assert all("5624" in i["host"] for i in d["items"])
        p1 = requests.get(f"{BASE_URL}/api/admin/logs", params={"page": 1, "size": 2}, headers=admin_h).json()
        p2 = requests.get(f"{BASE_URL}/api/admin/logs", params={"page": 2, "size": 2}, headers=admin_h).json()
        if p1["total"] > 2:
            assert {i["id"] for i in p1["items"]}.isdisjoint({i["id"] for i in p2["items"]})

    def test_texts_override(self, admin_h):
        try:
            r = requests.put(f"{BASE_URL}/api/admin/texts", json={"changes": [{"locale": "en", "key": "coursesHeading", "value": "TEST_hi {city}"}]}, headers=admin_h)
            assert r.status_code == 200 and r.json()["overrides"]["en"]["coursesHeading"] == "TEST_hi {city}"
            assert "TEST_hi Ottawa" in home("localhost:5623").text
        finally:
            r = requests.put(f"{BASE_URL}/api/admin/texts", json={"changes": [{"locale": "en", "key": "coursesHeading", "value": ""}]}, headers=admin_h)
            assert r.status_code == 200
        assert "Courses in and around Ottawa" in home("localhost:5623").text
        r = requests.put(f"{BASE_URL}/api/admin/texts", json={"changes": [{"locale": "en", "key": "nokey", "value": "x"}]}, headers=admin_h)
        assert r.status_code == 400

    def test_users_roles(self, admin_h, member_h):
        d = requests.get(f"{BASE_URL}/api/users", headers=admin_h).json()
        ids = {u["user_id"]: u["role"] for u in d["users"]}
        assert ids.get(ADMIN_ID) == "admin" and ids.get(MEMBER_ID) == "member"
        admins = [u for u, r in ids.items() if r == "admin"]
        try:
            r = requests.patch(f"{BASE_URL}/api/users/{MEMBER_ID}/role", json={"role": "admin"}, headers=admin_h)
            assert r.status_code == 200
            assert requests.get(f"{BASE_URL}/api/me", headers=member_h).json()["role"] == "admin"
        finally:
            r = requests.patch(f"{BASE_URL}/api/users/{MEMBER_ID}/role", json={"role": "member"}, headers=admin_h)
            assert r.status_code == 200
        if admins == [ADMIN_ID]:
            r = requests.patch(f"{BASE_URL}/api/users/{ADMIN_ID}/role", json={"role": "member"}, headers=admin_h)
            assert r.status_code == 409
        r = requests.patch(f"{BASE_URL}/api/users/{ADMIN_ID}/role", json={"role": "superuser"}, headers=admin_h)
        assert r.status_code == 403
        r = requests.patch(f"{BASE_URL}/api/users/user_nope/role", json={"role": "member"}, headers=admin_h)
        assert r.status_code == 404
