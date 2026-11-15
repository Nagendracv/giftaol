# Gift feature API tests: config, guest checkout/verify/pay, member checkout, my gifts, Harmony lookup/redeem, admin.
import asyncio
import hashlib
import hmac
import os

import pytest
import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

FRONT_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FRONT_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
ENV = dotenv_values("/app/backend/.env")
SECRET = ENV["CLERK_SECRET_KEY"]
ADMIN_ID = "user_3M7KxnjwE4wv1ipT9ol45VvhSRZ"
MEMBER_ID = "user_3M7KxqOlOVbqlOF5dzQWVHZdQzC"
TS_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"
CLERK_H = {"Authorization": f"Bearer {SECRET}", "User-Agent": "emergent-test"}


def mongo(fn):
    async def run():
        client = AsyncIOMotorClient(ENV["MONGO_URL"])
        try:
            return await fn(client[ENV["DB_NAME"]])
        finally:
            client.close()
    return asyncio.run(run())


def clerk_jwt(uid):
    s = requests.post("https://api.clerk.com/v1/sessions", json={"user_id": uid}, headers=CLERK_H, timeout=20).json()
    return requests.post(f"https://api.clerk.com/v1/sessions/{s['id']}/tokens", json={"expires_in_seconds": 3600}, headers=CLERK_H, timeout=20).json()["jwt"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {clerk_jwt(ADMIN_ID)}"}


@pytest.fixture(scope="module")
def member_h():
    return {"Authorization": f"Bearer {clerk_jwt(MEMBER_ID)}"}


def member_gift(h, amount=150):
    c = requests.post(f"{BASE_URL}/api/gifts/checkouts", json={"amount": amount, "message": "TEST_msg"}, headers=h, timeout=30)
    assert c.status_code == 200, c.text
    assert c.json()["status"] == "ready" and c.json()["guest"] is False
    p = requests.post(f"{BASE_URL}/api/gifts/checkouts/{c.json()['id']}/pay", json={"amount": amount}, headers=h, timeout=30)
    assert p.status_code == 200, p.text
    return p.json()["gift"]


# --- config & validation
def test_config():
    r = requests.get(f"{BASE_URL}/api/gifts/config", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["minAmount"] == 100 and d["currency"] == "CAD" and d["turnstileSiteKey"].startswith("1x0000")
    assert "rangeText" in d and d["maxMessage"] == 500


def test_out_of_range_and_missing_turnstile():
    r = requests.post(f"{BASE_URL}/api/gifts/checkouts", json={"amount": 50, "email": "delivered@resend.dev", "turnstileToken": TS_TOKEN}, timeout=20)
    assert r.status_code == 400
    r = requests.post(f"{BASE_URL}/api/gifts/checkouts", json={"amount": 120, "email": "delivered@resend.dev"}, timeout=20)
    assert r.status_code == 400
    r = requests.post(f"{BASE_URL}/api/gifts/checkouts", json={"amount": 120, "message": "x" * 501, "email": "delivered@resend.dev", "turnstileToken": TS_TOKEN}, timeout=20)
    assert r.status_code == 400


# --- guest flow
def test_guest_flow():
    r = requests.post(f"{BASE_URL}/api/gifts/checkouts", json={"amount": 120, "message": "TEST_guest", "recipientFirstName": "Ana",
                                                               "email": "TEST_guest1+clerk_test@example.com", "turnstileToken": TS_TOKEN}, timeout=30)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    assert r.json()["status"] == "verifying"
    assert requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/pay", json={"amount": 120}, timeout=20).status_code == 409
    assert requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/verify", json={"code": "000000"}, timeout=20).status_code == 400
    h = hmac.new(SECRET.encode(), f"{cid}:123456".encode(), hashlib.sha256).hexdigest()
    mongo(lambda db: db.gift_checkouts.update_one({"id": cid}, {"$set": {"verify_hash": h}}))
    v = requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/verify", json={"code": "123456"}, timeout=30)
    assert v.status_code == 200 and v.json()["status"] == "ready"
    assert isinstance(v.json().get("signInTicket"), str) and len(v.json()["signInTicket"]) > 20
    assert requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/pay", json={"amount": 50}, timeout=20).status_code == 400
    p = requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/pay", json={"amount": 130}, timeout=30)
    assert p.status_code == 200
    g = p.json()["gift"]
    assert g["amount"] == 130 and g["status"] == "active" and g["demo"] is True
    code = g["code"]
    assert len(code) == 19 and code.count("-") == 3
    assert not set(code.replace("-", "")) & set("0O1I")
    p2 = requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/pay", json={"amount": 130}, timeout=30)
    assert p2.json()["gift"]["id"] == g["id"]  # idempotent
    # the old sign-in endpoint was removed (security finding in iteration 6)
    assert requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/sign-in", timeout=30).status_code in (404, 405)


# --- member flow & dashboard
def test_member_flow_and_mine(member_h):
    g = member_gift(member_h, 150)
    mine = requests.get(f"{BASE_URL}/api/gifts/mine", headers=member_h, timeout=20)
    assert mine.status_code == 200 and any(x["id"] == g["id"] for x in mine.json()["gifts"])
    d = requests.get(f"{BASE_URL}/api/gifts/mine/{g['id']}", headers=member_h, timeout=20)
    assert d.status_code == 200 and d.json()["redemptions"] == []
    assert requests.get(f"{BASE_URL}/api/gifts/mine", timeout=20).status_code == 401
    r1 = requests.post(f"{BASE_URL}/api/gifts/mine/{g['id']}/resend-email", headers=member_h, timeout=60)
    assert r1.status_code == 200, r1.text
    r2 = requests.post(f"{BASE_URL}/api/gifts/mine/{g['id']}/resend-email", headers=member_h, timeout=30)
    assert r2.status_code == 429


def test_other_user_cannot_see_gift(member_h, admin_h):
    g = member_gift(member_h, 100)
    assert requests.get(f"{BASE_URL}/api/gifts/mine/{g['id']}", headers=admin_h, timeout=20).status_code == 404


# --- Harmony API
def test_harmony_lookup_redeem_lock(member_h, admin_h):
    g = member_gift(member_h, 200)
    code = g["code"]
    raw = code.replace("-", "").lower()
    for c in (code, raw, code.lower()):
        r = requests.get(f"{BASE_URL}/api/gift-codes/{c}", timeout=20)
        assert r.status_code == 200 and r.json()["balance"] == 200
    body = {"amount": 50, "courseName": "TEST_course", "courseReference": "TEST_ref1"}
    r = requests.post(f"{BASE_URL}/api/gift-codes/{raw}/redeem", json=body, timeout=20)
    assert r.status_code == 200 and r.json()["balance"] == 150 and r.json()["duplicate"] is False
    r = requests.post(f"{BASE_URL}/api/gift-codes/{raw}/redeem", json=body, timeout=20)
    assert r.json()["duplicate"] is True and r.json()["balance"] == 150
    d = requests.get(f"{BASE_URL}/api/gifts/mine/{g['id']}", headers=member_h, timeout=20).json()
    assert d["status"] == "partly_used" and len(d["redemptions"]) == 1
    statuses = []
    for i in range(5):
        r = requests.post(f"{BASE_URL}/api/gift-codes/{raw}/redeem", json={"amount": 999, "courseName": "T", "courseReference": f"TEST_x{i}"}, timeout=20)
        statuses.append(r.status_code)
    assert statuses == [409, 409, 409, 409, 423], statuses
    assert requests.get(f"{BASE_URL}/api/gift-codes/{raw}", timeout=20).status_code == 423
    r = requests.post(f"{BASE_URL}/api/gift-codes/{raw}/redeem", json={"amount": 1, "courseName": "T", "courseReference": "TEST_y"}, timeout=20)
    assert r.status_code == 423 and r.json()["message"] == "This code is temporarily locked."
    lst = requests.get(f"{BASE_URL}/api/admin/gifts", params={"q": raw[:8]}, headers=admin_h, timeout=20).json()
    assert any(i["id"] == g["id"] and i["locked"] for i in lst["items"])
    assert requests.post(f"{BASE_URL}/api/admin/gifts/{g['id']}/unlock", headers=admin_h, timeout=20).status_code == 200
    assert requests.get(f"{BASE_URL}/api/gift-codes/{raw}", timeout=20).status_code == 200
    r = requests.post(f"{BASE_URL}/api/gift-codes/{raw}/redeem", json={"amount": 150, "courseName": "T", "courseReference": "TEST_full"}, timeout=20)
    assert r.status_code == 200 and r.json()["status"] == "used_up" and r.json()["balance"] == 0
    r = requests.post(f"{BASE_URL}/api/gift-codes/{raw}/redeem", json={"amount": 1, "courseName": "T", "courseReference": "TEST_after"}, timeout=20)
    assert r.status_code == 409 and r.json()["error"] == "used_up"


def test_revoke(member_h, admin_h):
    g = member_gift(member_h, 100)
    assert requests.post(f"{BASE_URL}/api/admin/gifts/{g['id']}/revoke", headers=admin_h, timeout=20).status_code == 200
    assert requests.post(f"{BASE_URL}/api/admin/gifts/{g['id']}/revoke", headers=admin_h, timeout=20).status_code == 409
    r = requests.post(f"{BASE_URL}/api/gift-codes/{g['code']}/redeem", json={"amount": 1, "courseName": "T", "courseReference": "TEST_r"}, timeout=20)
    assert r.status_code == 409 and r.json()["error"] == "revoked"


def test_unknown_code():
    assert requests.get(f"{BASE_URL}/api/gift-codes/ABCDABCDABCDABCD", timeout=20).status_code == 404


# --- admin settings
def test_admin_settings(admin_h, member_h):
    assert requests.get(f"{BASE_URL}/api/admin/gift-settings", headers=member_h, timeout=20).status_code == 403
    assert requests.get(f"{BASE_URL}/api/admin/gift-settings", timeout=20).status_code == 401
    orig = requests.get(f"{BASE_URL}/api/admin/gift-settings", headers=admin_h, timeout=20).json()
    keep = {k: orig[k] for k in ("minAmount", "maxAmount", "wrongEntryCap", "presets")}
    try:
        bad = requests.put(f"{BASE_URL}/api/admin/gift-settings", json={**keep, "minAmount": 200, "maxAmount": 150}, headers=admin_h, timeout=20)
        assert bad.status_code == 422
        r = requests.put(f"{BASE_URL}/api/admin/gift-settings", json={"minAmount": 50, "maxAmount": 300, "wrongEntryCap": 3, "presets": [50, 75, 400]}, headers=admin_h, timeout=20)
        assert r.status_code == 200
        cfg = requests.get(f"{BASE_URL}/api/gifts/config", timeout=20).json()
        assert cfg["minAmount"] == 50 and cfg["maxAmount"] == 300 and cfg["presets"] == [50, 75]
        assert "300" in cfg["rangeText"]
    finally:
        requests.put(f"{BASE_URL}/api/admin/gift-settings", json=keep, headers=admin_h, timeout=20)
    assert requests.get(f"{BASE_URL}/api/gifts/config", timeout=20).json()["minAmount"] == keep["minAmount"]
