# Gift iteration 7: existing-account detection, signInTicket on verify, password claim endpoint, removed sign-in endpoint,
# Harmony valid-code lookup after unknown-code IP limit.
import time
from datetime import datetime, timezone

import pytest
import requests

from test_gifts_api import ADMIN_ID, BASE_URL, MEMBER_ID, SECRET, TS_TOKEN, CLERK_H, clerk_jwt, member_gift, mongo
import hashlib
import hmac

MEMBER_EMAIL = "member+clerk_test@example.com"
ADMIN_EMAIL = "admin+clerk_test@example.com"
CREATED = []


def guest_checkout(email, amount=120):
    for attempt in range(3):
        r = requests.post(f"{BASE_URL}/api/gifts/checkouts", json={"amount": amount, "message": "TEST_acct", "email": email,
                                                                   "turnstileToken": TS_TOKEN}, timeout=60)
        if r.status_code != 503:
            break
        time.sleep(30)
    assert r.status_code == 200, r.text
    CREATED.append(r.json()["id"])
    return r.json()


def set_code(cid):
    h = hmac.new(SECRET.encode(), f"{cid}:123456".encode(), hashlib.sha256).hexdigest()
    mongo(lambda db: db.gift_checkouts.update_one({"id": cid}, {"$set": {"verify_hash": h}}))


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    async def run(db):
        await db.gift_checkouts.delete_many({"id": {"$in": CREATED}})
    mongo(run)


@pytest.fixture(scope="module")
def tokens():
    return {"member": {"Authorization": f"Bearer {clerk_jwt(MEMBER_ID)}"}, "admin": {"Authorization": f"Bearer {clerk_jwt(ADMIN_ID)}"}}


def test_existing_account_flags_and_claim(tokens):
    c = guest_checkout(MEMBER_EMAIL)
    assert c["status"] == "verifying" and c["hasAccount"] is True and c["hasPassword"] is True
    cid = c["id"]
    assert requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/claim", timeout=20).status_code == 401
    r = requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/claim", headers=tokens["admin"], timeout=20)
    assert r.status_code == 403, r.text
    r = requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/claim", headers=tokens["member"], timeout=20)
    assert r.status_code == 200 and r.json()["status"] == "ready"
    g = requests.get(f"{BASE_URL}/api/gifts/checkouts/{cid}", timeout=20).json()
    assert g["status"] == "ready"
    doc = mongo(lambda db: db.gift_checkouts.find_one({"id": cid}, {"_id": 0}))
    assert doc["gift_giver_id"] == MEMBER_ID and "verify_hash" not in doc
    # claim on an already-ready checkout by another user must not change the owner
    r = requests.post(f"{BASE_URL}/api/gifts/checkouts/{cid}/claim", headers=tokens["admin"], timeout=20)
    doc = mongo(lambda db: db.gift_checkouts.find_one({"id": cid}, {"_id": 0}))
    assert doc["gift_giver_id"] == MEMBER_ID


def test_new_email_flags():
    time.sleep(15)
    c = guest_checkout("TEST_nobody_xyz+clerk_test@example.com")
    assert c["hasAccount"] is False and c["hasPassword"] is False


def test_existing_account_code_gives_ticket():
    time.sleep(15)
    c = guest_checkout(MEMBER_EMAIL)
    set_code(c["id"])
    v = requests.post(f"{BASE_URL}/api/gifts/checkouts/{c['id']}/verify", json={"code": "123456"}, timeout=30)
    assert v.status_code == 200 and v.json()["status"] == "ready"
    assert isinstance(v.json().get("signInTicket"), str)
    # second verify does not mint another ticket
    v2 = requests.post(f"{BASE_URL}/api/gifts/checkouts/{c['id']}/verify", json={"code": "123456"}, timeout=30)
    assert v2.status_code == 200 and not v2.json().get("signInTicket")


def test_admin_account_no_ticket():
    time.sleep(15)
    c = guest_checkout(ADMIN_EMAIL)
    assert c["hasAccount"] is True
    set_code(c["id"])
    v = requests.post(f"{BASE_URL}/api/gifts/checkouts/{c['id']}/verify", json={"code": "123456"}, timeout=30)
    assert v.status_code == 200 and v.json()["status"] == "ready"
    assert v.json().get("signInTicket") is None


def test_sign_in_endpoint_removed():
    assert requests.post(f"{BASE_URL}/api/gifts/checkouts/{CREATED[0]}/sign-in", timeout=20).status_code in (404, 405)


def test_harmony_valid_code_after_unknown_limit(tokens):
    start = datetime.now(timezone.utc)
    g = member_gift(tokens["member"], 100)
    codes = []
    for i in range(32):
        codes.append(requests.get(f"{BASE_URL}/api/gift-codes/ZZZZZZZZZZZZZZ{i:02d}", timeout=20).status_code)
    try:
        assert codes[-1] == 429, codes
        r = requests.get(f"{BASE_URL}/api/gift-codes/{g['code']}", timeout=20)
        assert r.status_code == 200 and r.json()["balance"] == 100
    finally:
        mongo(lambda db: db.gift_failed_lookups.delete_many({"at": {"$gte": start}}))
        requests.post(f"{BASE_URL}/api/admin/gifts/{g['id']}/revoke", headers=tokens["admin"], timeout=20)
