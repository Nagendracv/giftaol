"""giftaol.ca backend regression: auth, gifts, harmony API, wrong-entry lock, admin, hack monitor."""
import re
import uuid
from datetime import datetime, timezone

import requests
from conftest import API, DUMMY, ADMIN_EMAIL, code_hash, make_user

CODE_RE = re.compile(r"^[A-HJ-NP-Z2-9]{16}$")


def new_gift(s, amount=150, msg="TEST_msg", name="TEST_Bob"):
    r = s.post(f"{API}/gifts/checkout", json={"amount": amount, "message": msg, "recipient_first_name": name})
    assert r.status_code == 200, r.text
    pid = r.json()["payment_id"]
    r2 = s.post(f"{API}/payments/{pid}/demo-confirm")
    assert r2.status_code == 200, r2.text
    return pid, r2.json()


# ---- Auth ----
class TestAuth:
    def test_admin_login_cookie_and_me(self, admin_session):
        me = admin_session.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == ADMIN_EMAIL and me.json()["is_admin"] is True
        assert "access_token" in admin_session.cookies.get_dict()

    def test_login_sets_httponly_cookie(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "GiftAdmin#2026", "turnstile_token": DUMMY})
        assert r.status_code == 200
        sc = r.headers.get("set-cookie", "").lower()
        assert "httponly" in sc and "secure" in sc and "samesite=none" in sc

    def test_admin_hash_is_bcrypt(self, mdb):
        u = mdb.users.find_one({"email": ADMIN_EMAIL})
        assert u["password_hash"].startswith("$2b$")

    # /auth/me returns 200 null for anonymous (no 401 noise)
    def test_me_unauth_null(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 200 and r.json() is None

    def test_brute_force_lockout(self, mdb, created):
        email = f"test_lock_{uuid.uuid4().hex[:6]}@example.com"
        created["emails"].append(email)
        codes = [requests.post(f"{API}/auth/login", json={"email": email, "password": "wrongpass", "turnstile_token": DUMMY}).status_code
                 for _ in range(6)]
        assert codes[:5] == [401] * 5 and codes[5] == 429, codes

    def test_verify_code_creates_user(self, user_session, mdb):
        s, email, u = user_session
        assert u["email"] == email and u["is_admin"] is False and u["password_set"] is True
        assert mdb.users.find_one({"email": email})["password_hash"].startswith("$2b$")
        assert s.get(f"{API}/auth/me").json()["email"] == email

    def test_verify_code_wrong_code(self, mdb, created):
        email = f"test_wc_{uuid.uuid4().hex[:6]}@example.com"
        created["emails"].append(email)
        mdb.email_verifications.update_one({"email": email}, {"$set": {"code_hash": code_hash("111111"), "created_at": datetime.now(timezone.utc)}}, upsert=True)
        r = requests.post(f"{API}/auth/verify-code", json={"email": email, "code": "222222", "password": "TestPass123"})
        assert r.status_code == 400
        r = requests.post(f"{API}/auth/verify-code", json={"email": email, "code": "111111", "password": "short"})
        assert r.status_code == 400

    def test_request_code_daily_limit(self, mdb, created):
        email = f"test_lim_{uuid.uuid4().hex[:6]}@example.com"
        created["emails"].append(email)
        mdb.code_request_log.insert_many([{"id": uuid.uuid4().hex, "email": email, "requested_at": datetime.now(timezone.utc)} for _ in range(5)])
        r = requests.post(f"{API}/auth/request-code", json={"email": email, "turnstile_token": DUMMY})
        assert r.status_code == 429
        d = r.json()["detail"]
        assert d["code"] == "daily_limit" and "5 times today" in d["message"]

    def test_request_code_real_send(self, created):
        email = "delivered@resend.dev"
        created["emails"].append(email)
        r = requests.post(f"{API}/auth/request-code", json={"email": email, "turnstile_token": DUMMY})
        assert r.status_code == 200, r.text
        assert r.json()["sent"] is True

    def test_change_password(self, mdb, created):
        s, email, _ = make_user(mdb, created, "TEST_chpw")
        assert s.post(f"{API}/auth/change-password", json={"current_password": "bad", "new_password": "NewPass123"}).status_code == 400
        assert s.post(f"{API}/auth/change-password", json={"current_password": "TestPass123", "new_password": "NewPass123"}).status_code == 200
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "NewPass123", "turnstile_token": DUMMY})
        assert r.status_code == 200

    def test_non_admin_forbidden(self, user_session):
        s = user_session[0]
        for p in ["config", "content", "request-logs", "gifts/locked", "harmony-key"]:
            assert s.get(f"{API}/admin/{p}").status_code == 403, p
        assert s.post(f"{API}/admin/harmony-key/rotate").status_code == 403


# ---- Gifts + Harmony ----
class TestGiftsHarmony:
    def test_amount_below_min(self, user_session):
        r = user_session[0].post(f"{API}/gifts/checkout", json={"amount": 50})
        assert r.status_code == 400 and "100" in r.json()["detail"]

    def test_full_flow(self, admin_session, user_session, created):
        s = user_session[0]
        pid, g = new_gift(s, 150)
        created["gift_ids"].append(g["id"])
        assert CODE_RE.match(g["code"]) and g["amount"] == 150 and g["display_status"] == "active"
        # double confirm
        assert s.post(f"{API}/payments/{pid}/demo-confirm").status_code == 409
        mine = s.get(f"{API}/gifts/mine").json()
        assert any(x["id"] == g["id"] for x in mine)
        key = admin_session.post(f"{API}/admin/harmony-key/rotate").json()["key"]
        H = {"X-Harmony-Key": key}
        code = g["code"]
        assert requests.get(f"{API}/gifts/{code}").status_code == 401
        assert requests.get(f"{API}/gifts/{code}", headers={"X-Harmony-Key": "bad"}).status_code == 401
        dashed = "-".join(code[i:i + 4] for i in range(0, 16, 4))
        r = requests.get(f"{API}/gifts/{dashed}", headers=H)
        assert r.status_code == 200 and r.json() == {"status": "active", "balance": 150.0, "currency": "CAD"}
        ref = f"TEST_ref_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/gifts/{code}/redeem", headers=H, json={"amount_used": 50, "course_name": "TEST Happiness", "harmony_ref": ref})
        assert r.status_code == 200 and r.json()["balance"] == 100.0 and r.json()["idempotent_replay"] is False
        r = requests.post(f"{API}/gifts/{code}/redeem", headers=H, json={"amount_used": 50, "course_name": "TEST Happiness", "harmony_ref": ref})
        assert r.status_code == 200 and r.json()["idempotent_replay"] is True and r.json()["balance"] == 100.0
        r = requests.post(f"{API}/gifts/{code}/redeem", headers=H, json={"amount_used": 200, "course_name": "X", "harmony_ref": ref + "b"})
        assert r.status_code == 409
        d = s.get(f"{API}/gifts/mine/{g['id']}").json()
        assert d["display_status"] == "partly_used" and len(d["redemptions"]) == 1
        r = requests.post(f"{API}/gifts/{code}/redeem", headers=H, json={"amount_used": 100, "course_name": "TEST Sky", "harmony_ref": ref + "c"})
        assert r.status_code == 200 and r.json()["status"] == "used_up" and r.json()["balance"] == 0
        r = requests.post(f"{API}/gifts/{code}/redeem", headers=H, json={"amount_used": 1, "course_name": "X", "harmony_ref": ref + "d"})
        assert r.status_code == 409
        d = s.get(f"{API}/gifts/mine/{g['id']}").json()
        assert d["display_status"] == "used_up" and len(d["redemptions"]) == 2
        # other user can't see gift
        assert admin_session.get(f"{API}/gifts/mine/{g['id']}").status_code == 404

    def test_wrong_entry_lock_and_unlock(self, admin_session, user_session, created):
        s = user_session[0]
        _, g = new_gift(s, 120)
        created["gift_ids"].append(g["id"])
        key = admin_session.post(f"{API}/admin/harmony-key/rotate").json()["key"]
        H = {"X-Harmony-Key": key}
        code = g["code"]
        wrong = code[:8] + ("ZZZZZZZZ" if code[8:] != "ZZZZZZZZ" else "YYYYYYYY")
        for _ in range(5):
            assert requests.get(f"{API}/gifts/{wrong}", headers=H).status_code == 404
        r = requests.get(f"{API}/gifts/{code}", headers=H)
        assert r.status_code == 423 and r.json()["detail"] == "This code is temporarily locked."
        locked = admin_session.get(f"{API}/admin/gifts/locked").json()
        assert any(x["id"] == g["id"] for x in locked)
        assert admin_session.post(f"{API}/admin/gifts/{g['id']}/unlock").status_code == 200
        assert requests.get(f"{API}/gifts/{code}", headers=H).status_code == 200


# ---- Admin config/content/monitor ----
class TestAdmin:
    def test_config_min_max(self, admin_session, user_session, mdb):
        cfg = admin_session.get(f"{API}/admin/config").json()
        had_doc = mdb.app_config.find_one({"_id": "app"}) is not None
        body = {k: cfg[k] for k in ["min_amount", "max_amount", "payment_mode", "email_from_name", "email_reply_to",
                                    "code_request_limit", "wrong_entry_cap", "features", "texts"]}
        try:
            r = admin_session.put(f"{API}/admin/config", json={**body, "min_amount": 200, "max_amount": 500})
            assert r.status_code == 200 and r.json()["min_amount"] == 200
            assert requests.get(f"{API}/public/config").json()["max_amount"] == 500
            assert user_session[0].post(f"{API}/gifts/checkout", json={"amount": 150}).status_code == 400
            assert user_session[0].post(f"{API}/gifts/checkout", json={"amount": 600}).status_code == 400
            assert admin_session.put(f"{API}/admin/config", json={**body, "min_amount": 300, "max_amount": 200}).status_code == 400
            r = admin_session.put(f"{API}/admin/config", json={**body, "max_amount": None})
            assert r.json()["max_amount"] is None
        finally:
            if not had_doc:
                mdb.app_config.delete_one({"_id": "app"})
            else:
                admin_session.put(f"{API}/admin/config", json=body)
            mdb.payments.delete_many({"gift_giver_id": user_session[2]["id"], "gift_id": None})

    def test_content_save_and_rollback(self, admin_session, mdb):
        had = mdb.landing_content.find_one({"_id": "landing"}) is not None
        c = admin_session.get(f"{API}/admin/content").json()
        assert c["en"]["hero_title"]
        try:
            en = {**c["en"], "hero_title": "TEST_v1"}; fr = dict(c["fr"])
            assert admin_session.put(f"{API}/admin/content", json={"en": en, "fr": fr}).status_code == 200
            en = {**en, "hero_title": "TEST_v2"}; fr = {**fr, "hero_title": "TEST_v2_fr"}
            admin_session.put(f"{API}/admin/content", json={"en": en, "fr": fr})
            pub = requests.get(f"{API}/content").json()
            assert pub["en"]["hero_title"] == "TEST_v2" and pub["fr"]["hero_title"] == "TEST_v2_fr"
            r = admin_session.post(f"{API}/admin/content/rollback")
            assert r.status_code == 200 and r.json()["en"]["hero_title"] == "TEST_v1"
        finally:
            if not had:
                mdb.landing_content.delete_one({"_id": "landing"})
                mdb.landing_content_versions.delete_many({"en.hero_title": {"$in": ["TEST_v1", "TEST_v2"]}})

    def test_request_logs_and_masking(self, admin_session):
        requests.post(f"{API}/track", json={"path": "/TEST_trackpage", "referrer": "https://ref.example.com"})
        requests.get(f"{API}/gifts/ABCDEFGHJKLMNPQR")
        r = admin_session.get(f"{API}/admin/request-logs", params={"q": "TEST_trackpage", "kind": "page"})
        assert r.status_code == 200
        logs = r.json()["logs"]
        assert logs and logs[0]["kind"] == "page" and logs[0]["referrer"] == "https://ref.example.com"
        r = admin_session.get(f"{API}/admin/request-logs", params={"q": "/api/gifts/ABCD"}).json()["logs"]
        assert r and all("EFGH" not in x["path"] for x in r), [x["path"] for x in r[:3]]
        assert admin_session.get(f"{API}/admin/request-logs", params={"status": "4xx"}).json()["logs"][0]["status"] >= 400
