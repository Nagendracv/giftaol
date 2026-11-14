import os
import hmac
import secrets
from datetime import timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response, Depends
from pydantic import BaseModel, EmailStr, Field

from core import (db, now, new_id, hash_password, verify_password, hash_secret, client_ip, rate_limit,
                  verify_turnstile, set_session, public_user, get_current_user, get_optional_user, create_user, get_config,
                  fail, msg, lang_of)
from emailer import code_email, welcome_email, send_with_retry, send_email, spawn
from fastapi import HTTPException

router = APIRouter(prefix="/api/auth")
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


class RequestCodeIn(BaseModel):
    email: EmailStr
    turnstile_token: str = Field(min_length=1, max_length=4096)


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=20)
    password: str = Field(max_length=200)


class CodeLoginIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=20)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)
    turnstile_token: str = Field(min_length=1, max_length=4096)


class GoogleIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=500)


class LangIn(BaseModel):
    lang: str = Field(pattern="^(en|fr)$")


class ChangePasswordIn(BaseModel):
    current_password: Optional[str] = Field(default=None, max_length=200)
    new_password: str = Field(max_length=200)


@router.post("/request-code")
async def request_code(body: RequestCodeIn, request: Request):
    ip = client_ip(request)
    if not rate_limit(f"code-ip:{ip}", 15, 600):
        fail(request, "rate_limited", 429)
    if not await verify_turnstile(body.turnstile_token, ip):
        fail(request, "captcha_failed", 400)
    email = body.email.lower()
    cfg = await get_config()
    limit = int(cfg["code_request_limit"])
    count = await db.code_request_log.count_documents({"email": email, "requested_at": {"$gte": now() - timedelta(hours=24)}})
    if count >= limit:
        raise HTTPException(status_code=429, detail={"code": "daily_limit", "message": msg(request, "daily_limit", n=limit)})
    code = f"{secrets.randbelow(10 ** 6):06d}"
    subject, html = code_email(code, lang_of(request))
    ok, _, _ = await send_with_retry(email, subject, html)
    if not ok:
        fail(request, "email_failed", 503)
    await db.email_verifications.update_one(
        {"email": email},
        {"$set": {"code_hash": hash_secret(code), "created_at": now(), "wrong_attempts": 0}, "$setOnInsert": {"id": new_id()}},
        upsert=True,
    )
    await db.code_request_log.insert_one({"id": new_id(), "email": email, "requested_at": now()})
    existing = await db.users.find_one({"email": email}, {"_id": 0, "password_set": 1})
    return {"sent": True, "has_password": bool(existing and existing.get("password_set"))}


async def _consume_code(request: Request, email: str, code: str):
    if not rate_limit(f"verify:{email}", 10, 900) or not rate_limit(f"verify-ip:{client_ip(request)}", 30, 900):
        fail(request, "too_many_attempts", 429)
    entry = await db.email_verifications.find_one({"email": email}, {"_id": 0})
    if not entry or not hmac.compare_digest(entry["code_hash"], hash_secret(code.strip())):
        if entry:
            # After 10 wrong tries the code is discarded and a new one must be requested.
            res = await db.email_verifications.find_one_and_update(
                {"email": email}, {"$inc": {"wrong_attempts": 1}}, projection={"_id": 0, "wrong_attempts": 1}, return_document=True)
            if res and res.get("wrong_attempts", 0) >= 10:
                await db.email_verifications.delete_one({"email": email})
        fail(request, "invalid_code", 400)
    await db.email_verifications.delete_one({"email": email})


@router.post("/verify-code-login")
async def verify_code_login(body: CodeLoginIn, request: Request, response: Response):
    # Used by the guest gift flow: the code proves the email, no password needed yet.
    email = body.email.lower()
    await _consume_code(request, email, body.code)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user = await create_user(email, auth_method="email", lang=lang_of(request))
    set_session(response, user["id"])
    return public_user(user)


@router.post("/verify-code")
async def verify_code(body: VerifyCodeIn, request: Request, response: Response):
    email = body.email.lower()
    if len(body.password) < 8:
        fail(request, "password_short", 400)
    await _consume_code(request, email, body.code)
    pw_hash = hash_password(body.password)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if user:
        await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": pw_hash, "password_set": True, "lang": lang_of(request)}})
        user["password_set"] = True
    else:
        user = await create_user(email, auth_method="email", password_hash=pw_hash, lang=lang_of(request))
    set_session(response, user["id"])
    return public_user(user)


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    ip = client_ip(request)
    email = body.email.lower()
    if not rate_limit(f"login-ip:{ip}", 30, 600):
        fail(request, "rate_limited", 429)
    ident = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": ident}, {"_id": 0})
    if attempt and attempt.get("count", 0) >= 5:
        locked_at = attempt["last_at"]
        if locked_at.tzinfo is None:
            from datetime import timezone
            locked_at = locked_at.replace(tzinfo=timezone.utc)
        if now() - locked_at < timedelta(minutes=15):
            fail(request, "too_many_attempts", 429)
        await db.login_attempts.delete_one({"identifier": ident})
    if not await verify_turnstile(body.turnstile_token, ip):
        fail(request, "captcha_failed", 400)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash") or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one({"identifier": ident}, {"$inc": {"count": 1}, "$set": {"last_at": now()}}, upsert=True)
        fail(request, "invalid_credentials", 401)
    await db.login_attempts.delete_one({"identifier": ident})
    set_session(response, user["id"])
    return public_user(user)


@router.post("/google")
async def google_login(body: GoogleIn, request: Request, response: Response):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": body.session_id})
        r.raise_for_status()
        data = r.json()
    except Exception:
        fail(request, "google_failed", 401)
    email = (data.get("email") or "").lower()
    if not email:
        fail(request, "google_failed", 401)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user = await create_user(email, auth_method="google", name=data.get("name") or "", lang=lang_of(request))
        subject, html = welcome_email(lang_of(request))
        spawn(send_with_retry(email, subject, html))
    elif not user.get("name") and data.get("name"):
        await db.users.update_one({"id": user["id"]}, {"$set": {"name": data["name"]}})
    set_session(response, user["id"])
    return public_user(user)


@router.get("/me")
async def me(request: Request):
    # Returns null (200) for visitors who are not signed in, so anonymous page loads are not logged as 401s.
    user = await get_optional_user(request)
    return public_user(user) if user else None


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@router.put("/me/lang")
async def set_lang(body: LangIn, user=Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"lang": body.lang}})
    return {"ok": True}


@router.post("/change-password")
async def change_password(body: ChangePasswordIn, request: Request, user=Depends(get_current_user)):
    if not rate_limit(f"chpw:{user['id']}", 10, 900):
        fail(request, "too_many_attempts", 429)
    if len(body.new_password) < 8:
        fail(request, "password_short", 400)
    full = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    if full.get("password_set"):
        if not body.current_password or not verify_password(body.current_password, full["password_hash"]):
            fail(request, "wrong_password", 400)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(body.new_password), "password_set": True}})
    return {"ok": True}
