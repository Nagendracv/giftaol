# Guest gift flow: POST /api/auth/verify-code-login (code login without password) + checkout after login
import uuid
from datetime import datetime, timezone

import bcrypt
import pytest
import requests

from conftest import API, code_hash, ADMIN_EMAIL


def _seed(mdb, email, code="654321"):
    mdb.email_verifications.update_one(
        {"email": email},
        {"$set": {"code_hash": code_hash(code), "created_at": datetime.now(timezone.utc), "wrong_attempts": 0},
         "$setOnInsert": {"id": "TEST_" + uuid.uuid4().hex}}, upsert=True)


@pytest.fixture
def emails(mdb):
    created = []
    yield created
    for e in created:
        u = mdb.users.find_one({"email": e})
        if u:
            mdb.gifts.delete_many({"gift_giver_id": u["id"]})
            mdb.payments.delete_many({"gift_giver_id": u["id"]})
        mdb.users.delete_many({"email": e})
        mdb.email_verifications.delete_many({"email": e})


class TestVerifyCodeLogin:
    def test_wrong_code_400(self, mdb, emails):
        e = f"test_vcl_{uuid.uuid4().hex[:8]}@example.com"; emails.append(e)
        _seed(mdb, e)
        r = requests.post(f"{API}/auth/verify-code-login", json={"email": e, "code": "000000"})
        assert r.status_code == 400
        assert r.json()["detail"]
        assert "access_token" not in r.cookies
        assert mdb.users.find_one({"email": e}) is None
        assert mdb.email_verifications.find_one({"email": e})["wrong_attempts"] == 1

    def test_no_entry_400(self, emails):
        e = f"test_vcl_{uuid.uuid4().hex[:8]}@example.com"; emails.append(e)
        r = requests.post(f"{API}/auth/verify-code-login", json={"email": e, "code": "123456"})
        assert r.status_code == 400

    def test_validation_422(self):
        r = requests.post(f"{API}/auth/verify-code-login", json={"email": "bad", "code": "1"})
        assert r.status_code == 422
        r = requests.post(f"{API}/auth/verify-code-login", json={"email": "a@example.com", "code": ""})
        assert r.status_code == 422

    def test_new_user_created_and_logged_in(self, mdb, emails):
        e = f"TEST_vcl_{uuid.uuid4().hex[:8]}@example.com"; emails.append(e.lower())
        _seed(mdb, e.lower())
        s = requests.Session()
        r = s.post(f"{API}/auth/verify-code-login", json={"email": e, "code": " 654321 "})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["email"] == e.lower()
        assert d["password_set"] is False
        assert d["auth_method"] == "email"
        assert d["is_admin"] is False
        assert "access_token" in s.cookies
        assert "httponly" in r.headers.get("set-cookie", "").lower()
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200 and me.json()["email"] == e.lower()
        u = mdb.users.find_one({"email": e.lower()})
        assert u["password_set"] is False and u.get("password_hash") is None
        # code is consumed
        assert mdb.email_verifications.find_one({"email": e.lower()}) is None
        r2 = requests.post(f"{API}/auth/verify-code-login", json={"email": e, "code": "654321"})
        assert r2.status_code == 400
        # checkout + demo confirm works for the new user
        co = s.post(f"{API}/gifts/checkout", json={"amount": 150, "message": "TEST_guest", "recipient_first_name": None})
        assert co.status_code == 200, co.text
        g = s.post(f"{API}/payments/{co.json()['payment_id']}/demo-confirm")
        assert g.status_code == 200, g.text
        gid = g.json()["id"]
        gd = s.get(f"{API}/gifts/mine/{gid}")
        assert gd.status_code == 200

    def test_existing_user_password_unchanged(self, mdb, emails):
        e = f"test_vcl_{uuid.uuid4().hex[:8]}@example.com"; emails.append(e)
        ph = bcrypt.hashpw(b"OldPass#123", bcrypt.gensalt()).decode()
        uid = "TEST_" + uuid.uuid4().hex
        mdb.users.insert_one({"id": uid, "email": e, "name": "TEST", "password_hash": ph, "password_set": True,
                              "auth_method": "email", "is_admin": False, "lang": "en", "created_at": datetime.now(timezone.utc)})
        _seed(mdb, e)
        s = requests.Session()
        r = s.post(f"{API}/auth/verify-code-login", json={"email": e, "code": "654321"})
        assert r.status_code == 200
        assert r.json()["id"] == uid and r.json()["password_set"] is True
        u = mdb.users.find_one({"email": e})
        assert u["password_hash"] == ph
        assert mdb.users.count_documents({"email": e}) == 1

    def test_admin_untouched_regression_login(self, admin_session):
        me = admin_session.get(f"{API}/auth/me")
        assert me.status_code == 200 and me.json()["email"] == ADMIN_EMAIL and me.json()["is_admin"]

    def test_dashboard_api_protected(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 200 and r.json() is None
