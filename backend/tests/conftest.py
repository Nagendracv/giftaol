import os
import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE_ENV = dotenv_values("/app/frontend/.env")
BE_ENV = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FE_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"
DUMMY = "XXXX.DUMMY.TOKEN.XXXX"
ADMIN_EMAIL = "nagendracv@gmail.com"
ADMIN_PASSWORD = "GiftAdmin#2026"


def code_hash(code: str) -> str:
    return hmac.new(BE_ENV["JWT_SECRET"].encode(), code.encode(), hashlib.sha256).hexdigest()


@pytest.fixture(scope="session")
def mdb():
    c = MongoClient(BE_ENV["MONGO_URL"])
    yield c[BE_ENV["DB_NAME"]]
    c.close()


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "turnstile_token": DUMMY})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="session")
def created(mdb):
    """Track created records; cleanup by id at session end."""
    track = {"emails": [], "gift_ids": [], "payment_ids": []}
    yield track
    for e in track["emails"]:
        u = mdb.users.find_one({"email": e})
        if u:
            gids = [g["id"] for g in mdb.gifts.find({"gift_giver_id": u["id"]})]
            track["gift_ids"] += gids
            mdb.payments.delete_many({"gift_giver_id": u["id"]})
            mdb.users.delete_one({"id": u["id"]})
        mdb.email_verifications.delete_many({"email": e})
        mdb.code_request_log.delete_many({"email": e})
        mdb.login_attempts.delete_many({"identifier": {"$regex": f":{e}$"}})
    for gid in set(track["gift_ids"]):
        mdb.redemptions.delete_many({"gift_id": gid})
        mdb.gifts.delete_one({"id": gid})
    for pid in track["payment_ids"]:
        mdb.payments.delete_one({"id": pid})


def make_user(mdb, created, prefix="TEST_user"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@example.com".lower()
    created["emails"].append(email)
    mdb.email_verifications.update_one({"email": email}, {"$set": {"code_hash": code_hash("123456"),
                                        "created_at": datetime.now(timezone.utc), "id": uuid.uuid4().hex}}, upsert=True)
    s = requests.Session()
    r = s.post(f"{API}/auth/verify-code", json={"email": email, "code": "123456", "password": "TestPass123"})
    assert r.status_code == 200, r.text
    return s, email, r.json()


@pytest.fixture(scope="session")
def user_session(mdb, created):
    return make_user(mdb, created)
