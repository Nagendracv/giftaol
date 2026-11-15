"""End-to-end checks of the FastAPI app with Host headers (AC-1, 2, 3, 11, 12, 14, 6)."""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import server  # noqa: E402
from i18n import Texts  # noqa: E402
from site_config import load_config_file, validate_config  # noqa: E402
from state import STATE  # noqa: E402


class FakeFeed:
    async def get(self, months):
        return [], False


async def fake_event(*args, **kwargs):
    return None


def body_text(html: str) -> str:
    return re.search(r'data-testid="courses-heading">([^<]*)<', html).group(1)


@pytest.fixture
def client(app_client, monkeypatch):
    monkeypatch.setattr(server, "record_visit", lambda *a, **k: None)  # keep test visits out of the real access log
    monkeypatch.setattr(STATE, "feeds", {"en": FakeFeed(), "fr": FakeFeed()})  # never call the shared Unity API from tests
    monkeypatch.setattr(server, "record_event", fake_event)
    saved = (STATE.config, STATE.texts.overrides)
    # Use the local file config regardless of admin edits saved in the database.
    STATE.config = validate_config(load_config_file(BACKEND / "config/sites.local.json"), {"en", "fr"})
    STATE.texts.overrides = {}
    yield app_client
    STATE.config, STATE.texts.overrides = saved


class TestApp:
    def test_ac1_ottawa_home(self, client):
        r = client.get("/", headers={"Host": "localhost:5623"})
        assert r.status_code == 200
        assert body_text(r.text) == "Courses in and around Ottawa"

    def test_ac2_mississauga_home(self, client):
        r = client.get("/", headers={"Host": "localhost:5624"})
        assert r.status_code == 200 and body_text(r.text) == "Courses in and around Mississauga"

    def test_ac3_unknown_host_404_and_warning(self, client, caplog):
        with caplog.at_level(logging.WARNING, logger="citysites"):
            r = client.get("/", headers={"Host": "unknown.example"})
        assert r.status_code == 404
        assert "This site is not configured" in r.text and "Courses in and around" not in r.text
        assert any("unknown.example" in rec.getMessage() for rec in caplog.records if rec.levelno == logging.WARNING)

    def test_ac4_ac5_case_and_default_port(self, client):
        assert body_text(client.get("/", headers={"Host": "AOLOTTAWA.CA"}).text) == "Courses in and around Ottawa"
        assert body_text(client.get("/", headers={"Host": "aolottawa.ca:443"}).text) == "Courses in and around Ottawa"

    def test_ac11_healthz_any_host(self, client):
        for host in ("unknown.example", "localhost:5623"):
            assert client.get("/healthz", headers={"Host": host}).status_code == 200

    def test_ac12_logs_include_city(self, client, caplog):
        with caplog.at_level(logging.INFO, logger="citysites"):
            client.get("/", headers={"Host": "localhost:5623"})
            client.get("/", headers={"Host": "nowhere.example"})
        lines = [rec.getMessage() for rec in caplog.records]
        assert any("cityId=ottawa" in m for m in lines) and any("cityId=unknown" in m for m in lines)

    def test_forwarded_host_only_when_trusted(self, client, monkeypatch):
        headers = {"Host": "unknown.example", "X-Forwarded-Host": "localhost:5624"}
        monkeypatch.setattr(server, "TRUST_PROXY", True)
        assert body_text(client.get("/", headers=headers).text) == "Courses in and around Mississauga"
        monkeypatch.setattr(server, "TRUST_PROXY", False)
        assert client.get("/", headers=headers).status_code == 404

    def test_french_via_switcher(self, client):
        r = client.get("/?lang=fr", headers={"Host": "localhost:5623"}, follow_redirects=False)
        assert r.status_code == 303 and "lang=fr" in r.headers["set-cookie"]
        client.cookies.set("lang", "fr")
        assert body_text(client.get("/", headers={"Host": "localhost:5623"}).text) == "Cours à Ottawa et dans les environs"
        client.cookies.clear()

    def test_header_shows_dashboard_when_signed_in(self, client):
        client.cookies.set("__client_uat", "1700000000")
        html = client.get("/", headers={"Host": "localhost:5623"}).text
        assert 'href="/dashboard"' in html and 'data-testid="auth-button"' not in html
        client.cookies.set("__client_uat", "0")
        assert 'data-testid="auth-button"' in client.get("/", headers={"Host": "localhost:5623"}).text
        client.cookies.clear()

    def test_ac14_text_comes_from_resource_file(self, client, tmp_path):
        (tmp_path / "en.json").write_text(json.dumps({**STATE.texts.files["en"], "coursesHeading": "Welcome to {city}"}))
        original = STATE.texts
        STATE.texts = Texts(tmp_path)
        try:
            assert body_text(client.get("/", headers={"Host": "localhost:5623"}).text) == "Welcome to Ottawa"
        finally:
            STATE.texts = original


def test_ac6_startup_fails_on_bad_config(tmp_path):
    bad = {"cities": [
        {"cityId": "ottawa", "displayName": "Ottawa", "timezone": "America/Toronto", "hosts": ["x.ca"], "nearbyCityIds": ["nowhere"]},
        {"cityId": "missi", "displayName": "Missi", "timezone": "America/Toronto", "hosts": ["x.ca"]},
    ]}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    env = {**os.environ, "SITE_CONFIG_FILE": str(path)}
    proc = subprocess.run([sys.executable, "-c", "import server"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert proc.returncode != 0
    assert "listed under both 'ottawa' and 'missi'" in proc.stderr
    assert "references unknown city 'nowhere'" in proc.stderr
