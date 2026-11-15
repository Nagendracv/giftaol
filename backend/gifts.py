"""Gift purchase flow: checkout, guest email verification, demo payment, code generation and the giver's dashboard."""

import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx
import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

from clerk_auth import require_user
from course_pages import fill
from db import db
from emailer import EmailUnavailable
from gift_emails import format_code, money, send_gift, send_verification
from reminders import EMAIL_RE
from roles import current_member
from state import STATE

logger = logging.getLogger("citysites")
router = APIRouter(prefix="/api")

CURRENCY = "CAD"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
CODE_LENGTH = 16
DEFAULT_SETTINGS = {"minAmount": 100, "maxAmount": None, "wrongEntryCap": 5, "presets": [100, 150, 250, 500]}
MAX_MESSAGE = 500
MAX_NAME = 60
VERIFY_TTL = timedelta(minutes=15)
VERIFY_MAX_TRIES = 5
VERIFY_MAX_SENDS = 5
VERIFY_COOLDOWN = timedelta(seconds=60)
CHECKOUTS_PER_IP_HOUR = 10
RESEND_COOLDOWN = timedelta(minutes=10)
RESENDS_PER_DAY = 5
BACKGROUND_DELAYS = (5, 20, 60)
INTERACTIVE_DELAYS = (2, 4)


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt


async def gift_settings() -> dict:
    doc = await db.gift_settings.find_one({"_id": "current"}, {"_id": 0})
    return {**DEFAULT_SETTINGS, **(doc or {})}


def to_cents(value) -> int | None:
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    return int(d * 100) if d.is_finite() and d > 0 else None


def range_text(settings: dict, texts: dict, locale: str) -> str:
    low = money(int(settings["minAmount"] * 100), locale)
    if settings.get("maxAmount") is None:
        return fill(texts["giftAllowedMin"], min=low)
    return fill(texts["giftAllowedRange"], min=low, max=money(int(settings["maxAmount"] * 100), locale))


def in_range(cents: int | None, settings: dict) -> bool:
    if cents is None or cents < int(settings["minAmount"] * 100):
        return False
    return settings.get("maxAmount") is None or cents <= int(settings["maxAmount"] * 100)


def context(request: Request):
    from server import client_ip, pick_locale  # avoid a circular import at load time
    city = request.state.city
    if city is None:
        raise HTTPException(status_code=404, detail="This site is not configured")
    locale = pick_locale(request, city)
    return city, locale, STATE.texts.bundle(locale), client_ip(request)


def optional_user(request: Request) -> dict | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer ") or len(auth) < 20:
        return None
    return require_user(request)


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(raw: str) -> str:
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def _hash(value: str) -> str:
    return hmac.new(os.environ["CLERK_SECRET_KEY"].encode(), value.encode(), hashlib.sha256).hexdigest()


def gift_status(gift: dict) -> str:
    if gift["status"] in ("revoked", "used_up"):
        return gift["status"]
    if gift.get("locked"):
        return "locked"
    return "partly_used" if gift["balance_cents"] < gift["amount_cents"] else "active"


def gift_view(gift: dict, redemptions: list | None = None) -> dict:
    view = {"id": gift["id"], "code": format_code(gift["code"]), "amount": gift["amount_cents"] / 100,
            "balance": gift["balance_cents"] / 100, "currency": gift["currency"], "message": gift.get("message", ""),
            "recipientFirstName": gift.get("recipient_first_name", ""), "status": gift_status(gift),
            "createdAt": aware(gift["created_at"]).isoformat(), "demo": gift.get("demo", False),
            "emailStatus": gift.get("email_status", "pending"), "email": gift["gift_giver_email"],
            "lastRedeemedAt": aware(gift.get("last_redeemed_at")).isoformat() if gift.get("last_redeemed_at") else None}
    if redemptions is not None:
        view["redemptions"] = [{"courseName": r["course_name"], "courseReference": r["course_reference"],
                                "amountUsed": r["amount_cents"] / 100, "balanceAfter": r["balance_after_cents"] / 100,
                                "date": aware(r["created_at"]).isoformat()} for r in redemptions]
    return view


async def redemptions_for(gift_ids: list) -> dict:
    grouped: dict = {gid: [] for gid in gift_ids}
    async for r in db.gift_redemptions.find({"gift_id": {"$in": gift_ids}}, {"_id": 0}).sort("created_at", -1):
        grouped[r["gift_id"]].append(r)
    return grouped


async def send_with_retry(send, delays: tuple, label: str) -> bool:
    """Run `send` once plus once per delay (seconds of backoff); the provider briefly rate-limits bursts."""
    for attempt, delay in enumerate((0, *delays)):
        if delay:
            await asyncio.sleep(delay)
        try:
            await send()
            return True
        except (EmailUnavailable, ValueError) as exc:
            logger.warning("%s: attempt %d failed: %s", label, attempt + 1, exc)
    return False


async def deliver_gift_email(gift_id: str, delays: tuple = BACKGROUND_DELAYS) -> bool:
    """Send the gift email with retries and record the outcome; the hourly job retries failures."""
    gift = await db.gifts.find_one({"id": gift_id}, {"_id": 0})
    city = STATE.config.cities.get(gift["city_id"])
    texts = STATE.texts.bundle(gift["locale"])
    ok = await send_with_retry(lambda: send_gift(gift, city, texts), delays, f"Gift email {gift_id}")
    update = {"email_status": "sent", "email_last_sent_at": now()} if ok else {"email_status": "failed"}
    await db.gifts.update_one({"id": gift_id}, {"$set": update, "$inc": {"email_attempts": 1}})
    return ok


async def retry_failed_gift_emails() -> int:
    sent = 0
    async for g in db.gifts.find({"email_status": "failed", "email_attempts": {"$lt": 24},
                                  "created_at": {"$gte": now() - timedelta(days=3)}}, {"_id": 0, "id": 1}):
        sent += await deliver_gift_email(g["id"], delays=())
    return sent


# --- Turnstile and Clerk -------------------------------------------------------

async def turnstile_ok(token: str, ip: str) -> bool:
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                                  data={"secret": os.environ["TURNSTILE_SECRET_KEY"], "response": token, "remoteip": ip})
        return bool(r.json().get("success"))
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Turnstile check failed: %s", exc)
        return False


def _clerk(method: str, path: str, **kwargs):
    r = requests.request(method, f"https://api.clerk.com/v1{path}", timeout=10, **kwargs,
                         headers={"Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}", "User-Agent": "emergent-app"})
    r.raise_for_status()
    return r.json()


def clerk_account(email: str) -> dict | None:
    found = _clerk("GET", "/users", params={"email_address": email, "limit": 1})
    return found[0] if found else None


async def account_info(email: str) -> dict:
    try:
        user = await run_in_threadpool(clerk_account, email)
    except requests.RequestException as exc:
        logger.error("Clerk lookup failed: %s", exc)
        return {"has_account": False, "has_password": False}
    return {"has_account": user is not None, "has_password": bool(user and user.get("password_enabled"))}


def _admin_email(email: str) -> bool:
    return email.lower() in {e.strip().lower() for e in os.environ.get("ADMIN_EMAIL", "").split(",") if e.strip()}


async def sign_in_ticket(user_id: str | None, email: str) -> str | None:
    """Short-lived one-time Clerk sign-in, handed out only right after the email code is checked (never for admins)."""
    if not user_id or _admin_email(email) or await db.users.find_one({"user_id": user_id, "role": "admin"}, {"_id": 1}):
        return None
    try:
        token = await run_in_threadpool(_clerk, "POST", "/sign_in_tokens", json={"user_id": user_id, "expires_in_seconds": 120})
        return token["token"]
    except requests.RequestException as exc:
        logger.error("Sign-in token failed: %s", exc)
        return None


def find_or_create_clerk_user(email: str) -> str:
    found = _clerk("GET", "/users", params={"email_address": email, "limit": 1})
    if found:
        return found[0]["id"]
    try:
        return _clerk("POST", "/users", json={"email_address": [email], "skip_password_requirement": True})["id"]
    except requests.HTTPError:
        found = _clerk("GET", "/users", params={"email_address": email, "limit": 1})
        if found:
            return found[0]["id"]
        raise


# --- Checkout ------------------------------------------------------------------

class CheckoutIn(BaseModel):
    amount: float | str
    message: str = ""
    recipientFirstName: str = ""
    email: str = ""
    turnstileToken: str = ""


def checkout_view(c: dict, gift: dict | None = None) -> dict:
    view = {"id": c["id"], "status": c["status"], "email": c["email"], "amount": c["amount_cents"] / 100,
            "message": c["message"], "recipientFirstName": c["recipient_first_name"], "guest": c["guest"],
            "hasAccount": c.get("has_account", False), "hasPassword": c.get("has_password", False),
            "verifySentAt": aware(c.get("verify_sent_at")).isoformat() if c.get("verify_sent_at") else None}
    if gift:
        view["gift"] = gift_view(gift)
    return view


async def _issue_verification(c: dict, city: dict, texts: dict) -> None:
    code = f"{secrets.randbelow(1_000_000):06d}"
    await db.gift_checkouts.update_one({"id": c["id"]}, {
        "$set": {"verify_hash": _hash(f'{c["id"]}:{code}'), "verify_expires": now() + VERIFY_TTL,
                 "verify_attempts": 0, "verify_sent_at": now()}, "$inc": {"verify_sends": 1}})
    if not await send_with_retry(lambda: send_verification(c, code, city, texts), INTERACTIVE_DELAYS, f"Verification {c['id']}"):
        raise EmailUnavailable("verification email not sent")


@router.get("/gifts/config")
async def public_config(request: Request):
    city, locale, texts, _ = context(request)
    s = await gift_settings()
    presets = [p for p in s["presets"] if in_range(int(p * 100), s)]
    return {"minAmount": s["minAmount"], "maxAmount": s["maxAmount"], "presets": presets, "currency": CURRENCY,
            "rangeText": range_text(s, texts, locale), "maxMessage": MAX_MESSAGE,
            "turnstileSiteKey": os.environ["TURNSTILE_SITE_KEY"]}


@router.post("/gifts/checkouts")
async def create_checkout(body: CheckoutIn, request: Request):
    city, locale, texts, ip = context(request)
    s = await gift_settings()
    cents = to_cents(body.amount)
    if not in_range(cents, s):
        raise HTTPException(status_code=400, detail=fill(texts["giftAmountOutOfRange"], range=range_text(s, texts, locale)))
    message, name = body.message.strip(), body.recipientFirstName.strip()
    if len(message) > MAX_MESSAGE or len(name) > MAX_NAME:
        raise HTTPException(status_code=400, detail=texts["giftTooLong"])
    user = optional_user(request)
    if user:
        member = await current_member(user)
        email, giver_id = member["email"].lower(), user["user_id"]
    else:
        email, giver_id = body.email.strip().lower(), None
        if not EMAIL_RE.match(email) or len(email) > 254:
            raise HTTPException(status_code=400, detail=texts["reminderBadEmail"])
        if await db.gift_checkouts.count_documents({"ip": ip, "created_at": {"$gte": now() - timedelta(hours=1)}}) >= CHECKOUTS_PER_IP_HOUR:
            raise HTTPException(status_code=429, detail=texts["reminderTooMany"])
        if not await turnstile_ok(body.turnstileToken, ip):
            raise HTTPException(status_code=400, detail=texts["giftRobotCheck"])
    c = {"id": secrets.token_urlsafe(24), "city_id": city["cityId"], "host": request.state.host, "locale": locale,
         "email": email, "gift_giver_id": giver_id, "guest": user is None, "amount_cents": cents, "message": message,
         "recipient_first_name": name, "status": "ready" if user else "verifying", "verify_sends": 0,
         "ip": ip, "created_at": now(), **(await account_info(email) if not user else {})}
    await db.gift_checkouts.insert_one(dict(c))
    if not user:
        try:
            await _issue_verification(c, city, texts)
        except (EmailUnavailable, ValueError):
            await db.gift_checkouts.delete_one({"id": c["id"]})
            raise HTTPException(status_code=503, detail=texts["reminderEmailDown"])
        c = await db.gift_checkouts.find_one({"id": c["id"]}, {"_id": 0})
    return checkout_view(c)


async def _checkout(checkout_id: str, texts: dict) -> dict:
    c = await db.gift_checkouts.find_one({"id": checkout_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail=texts["giftNotFound"])
    return c


@router.get("/gifts/checkouts/{checkout_id}")
async def get_checkout(checkout_id: str, request: Request):
    _, _, texts, _ = context(request)
    c = await _checkout(checkout_id, texts)
    gift = await db.gifts.find_one({"id": c["gift_id"]}, {"_id": 0}) if c.get("gift_id") else None
    return checkout_view(c, gift)


@router.post("/gifts/checkouts/{checkout_id}/resend-code")
async def resend_code(checkout_id: str, request: Request):
    city, _, texts, _ = context(request)
    c = await _checkout(checkout_id, texts)
    if c["status"] != "verifying":
        return checkout_view(c)
    if c.get("verify_sends", 0) >= VERIFY_MAX_SENDS or aware(c.get("verify_sent_at")) > now() - VERIFY_COOLDOWN:
        raise HTTPException(status_code=429, detail=texts["giftWaitResend"])
    try:
        await _issue_verification(c, city, texts)
    except (EmailUnavailable, ValueError):
        raise HTTPException(status_code=503, detail=texts["reminderEmailDown"])
    return checkout_view(await _checkout(checkout_id, texts))


class CodeIn(BaseModel):
    code: str


@router.post("/gifts/checkouts/{checkout_id}/verify")
async def verify_code(checkout_id: str, body: CodeIn, request: Request):
    _, _, texts, _ = context(request)
    c = await _checkout(checkout_id, texts)
    if c["status"] != "verifying":
        return checkout_view(c)
    if aware(c["verify_expires"]) < now() or c.get("verify_attempts", 0) >= VERIFY_MAX_TRIES:
        raise HTTPException(status_code=410, detail=texts["giftCodeExpired"])
    code = "".join(ch for ch in body.code if ch.isdigit())
    if not hmac.compare_digest(c["verify_hash"], _hash(f"{checkout_id}:{code}")):
        await db.gift_checkouts.update_one({"id": checkout_id}, {"$inc": {"verify_attempts": 1}})
        raise HTTPException(status_code=400, detail=texts["giftCodeWrong"])
    giver_id = None
    try:
        giver_id = await run_in_threadpool(find_or_create_clerk_user, c["email"])
    except requests.RequestException as exc:
        logger.error("Could not create the giver's account for checkout %s: %s", checkout_id, exc)
    c = await db.gift_checkouts.find_one_and_update(
        {"id": checkout_id, "status": "verifying"},
        {"$set": {"status": "ready", "gift_giver_id": giver_id, "verified_at": now()}, "$unset": {"verify_hash": ""}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not c:
        return checkout_view(await _checkout(checkout_id, texts))
    return {**checkout_view(c), "signInTicket": await sign_in_ticket(giver_id, c["email"])}


@router.post("/gifts/checkouts/{checkout_id}/claim")
async def claim_checkout(checkout_id: str, request: Request, user: dict = Depends(require_user)):
    """A guest who signed in with their password instead of the code: their account email proves ownership."""
    _, _, texts, _ = context(request)
    c = await _checkout(checkout_id, texts)
    member = await current_member(user)
    if c["status"] != "verifying":
        return checkout_view(c)
    if member.get("email", "").lower() != c["email"]:
        raise HTTPException(status_code=403, detail=texts["giftOtherAccount"])
    c = await db.gift_checkouts.find_one_and_update(
        {"id": checkout_id, "status": "verifying"},
        {"$set": {"status": "ready", "gift_giver_id": user["user_id"], "verified_at": now()}, "$unset": {"verify_hash": ""}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    return checkout_view(c or await _checkout(checkout_id, texts))


class PayIn(BaseModel):
    amount: float | str


async def _create_gift(c: dict, cents: int) -> dict:
    # Demo provider: the browser's Pay click is the confirmation. A real provider must create the
    # gift only from a verified payment event (webhook or server-side API check), never from a redirect.
    payment = {"payment_id": str(uuid.uuid4()), "gift_giver_id": c["gift_giver_id"], "gift_giver_email": c["email"],
               "amount_cents": cents, "currency": CURRENCY, "provider": "demo", "provider_ref": f"demo_{secrets.token_hex(8)}",
               "status": "succeeded", "checkout_id": c["id"], "created_at": now()}
    await db.gift_payments.insert_one(dict(payment))
    gift = {"id": str(uuid.uuid4()), "gift_giver_id": c["gift_giver_id"], "gift_giver_email": c["email"],
            "amount_cents": cents, "balance_cents": cents, "currency": CURRENCY, "message": c["message"],
            "recipient_first_name": c["recipient_first_name"], "status": "active", "locked": False, "wrong_entries": 0,
            "created_at": now(), "last_redeemed_at": None, "payment_id": payment["payment_id"], "demo": True,
            "city_id": c["city_id"], "host": c["host"], "locale": c["locale"], "email_status": "pending",
            "email_attempts": 0, "resends": []}
    for _ in range(5):
        gift["code"] = new_code()
        try:
            await db.gifts.insert_one(dict(gift))
            return gift
        except DuplicateKeyError:
            continue
    raise HTTPException(status_code=500, detail="Could not generate a unique code")


@router.post("/gifts/checkouts/{checkout_id}/pay")
async def pay(checkout_id: str, body: PayIn, request: Request, background: BackgroundTasks):
    _, locale, texts, _ = context(request)
    c = await _checkout(checkout_id, texts)
    if c["status"] == "paid":
        return checkout_view(c, await db.gifts.find_one({"id": c["gift_id"]}, {"_id": 0}))
    if c["status"] != "ready":
        raise HTTPException(status_code=409, detail=texts["giftVerifyFirst"])
    s = await gift_settings()
    cents = to_cents(body.amount)
    if not in_range(cents, s):
        raise HTTPException(status_code=400, detail=fill(texts["giftAmountOutOfRange"], range=range_text(s, texts, locale)))
    c = await db.gift_checkouts.find_one_and_update({"id": checkout_id, "status": "ready"}, {"$set": {"status": "paying"}},
                                                    projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not c:
        raise HTTPException(status_code=409, detail=texts["giftVerifyFirst"])
    try:
        gift = await _create_gift(c, cents)
    except Exception:
        await db.gift_checkouts.update_one({"id": checkout_id}, {"$set": {"status": "ready"}})
        raise
    c = await db.gift_checkouts.find_one_and_update(
        {"id": checkout_id}, {"$set": {"status": "paid", "gift_id": gift["id"], "amount_cents": cents}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    background.add_task(deliver_gift_email, gift["id"])
    return checkout_view(c, gift)


# --- Giver dashboard -----------------------------------------------------------

def _owner_query(member: dict) -> dict:
    ors = [{"gift_giver_id": member["user_id"]}]
    if member.get("email"):
        ors.append({"gift_giver_email": member["email"].lower()})
    return {"$or": ors}


@router.get("/gifts/mine")
async def my_gifts(user: dict = Depends(require_user)):
    member = await current_member(user)
    gifts = await db.gifts.find(_owner_query(member), {"_id": 0}).sort("created_at", -1).to_list(500)
    grouped = await redemptions_for([g["id"] for g in gifts])
    return {"email": member.get("email", ""), "gifts": [gift_view(g, grouped[g["id"]]) for g in gifts]}


async def _my_gift(gift_id: str, user: dict) -> dict:
    member = await current_member(user)
    gift = await db.gifts.find_one({"id": gift_id, **_owner_query(member)}, {"_id": 0})
    if not gift:
        raise HTTPException(status_code=404, detail="Gift not found")
    return gift


@router.get("/gifts/mine/{gift_id}")
async def my_gift(gift_id: str, user: dict = Depends(require_user)):
    gift = await _my_gift(gift_id, user)
    return gift_view(gift, (await redemptions_for([gift_id]))[gift_id])


@router.post("/gifts/mine/{gift_id}/resend-email")
async def resend_gift_email(gift_id: str, request: Request, user: dict = Depends(require_user)):
    _, _, texts, _ = context(request)
    gift = await _my_gift(gift_id, user)
    recent = [aware(t) for t in gift.get("resends", []) if aware(t) > now() - timedelta(days=1)]
    if len(recent) >= RESENDS_PER_DAY or (recent and max(recent) > now() - RESEND_COOLDOWN):
        raise HTTPException(status_code=429, detail=texts["giftResendWait"])
    if not await deliver_gift_email(gift_id, delays=INTERACTIVE_DELAYS):
        raise HTTPException(status_code=503, detail=texts["reminderEmailDown"])
    await db.gifts.update_one({"id": gift_id}, {"$set": {"resends": recent + [now()]}})
    return {"message": texts["giftResent"]}
