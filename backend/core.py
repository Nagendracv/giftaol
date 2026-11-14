import os
import re
import copy
import hmac
import time
import uuid
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import bcrypt
import jwt
import httpx
from fastapi import Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient

from defaults import DEFAULT_CONFIG, DEFAULT_CONTENT

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ["JWT_SECRET"]
TURNSTILE_SECRET = os.environ["TURNSTILE_SECRET_KEY"]
DEMO_PAYMENTS_ENABLED = os.environ.get("DEMO_PAYMENTS_ENABLED", "false").lower() == "true"
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]
SESSION_DAYS = 7
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
logger = logging.getLogger("giftaol")


def now():
    return datetime.now(timezone.utc)


def ser(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def new_id():
    return uuid.uuid4().hex


# ---------- hashing ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def hash_secret(value: str) -> str:
    return hmac.new(JWT_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


# ---------- money / codes ----------
def to_cents(amount: float) -> int:
    return int(round(float(amount) * 100))


def dollars(cents: int) -> float:
    return round((cents or 0) / 100, 2)


def normalize_code(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw or "").upper()


def format_code(code: str) -> str:
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def mask_code(code: str) -> str:
    return (code[:4] + "-****-****-****") if code else ""


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(16))


# ---------- i18n messages ----------
MSG = {
    "daily_limit": {"en": "A code has already been sent to this email {n} times today. Please try again tomorrow.",
                    "fr": "Un code a déjà été envoyé à cette adresse {n} fois aujourd'hui. Veuillez réessayer demain."},
    "captcha_failed": {"en": "Please complete the security check and try again.",
                       "fr": "Veuillez compléter la vérification de sécurité et réessayer."},
    "invalid_code": {"en": "That code is not correct. Check the latest email we sent and try again.",
                     "fr": "Ce code n'est pas valide. Vérifiez le dernier courriel envoyé et réessayez."},
    "invalid_credentials": {"en": "The email or password is not correct.",
                            "fr": "Le courriel ou le mot de passe est incorrect."},
    "too_many_attempts": {"en": "Too many failed attempts. Please wait 15 minutes and try again.",
                          "fr": "Trop de tentatives échouées. Veuillez attendre 15 minutes et réessayer."},
    "rate_limited": {"en": "Too many requests. Please wait a few minutes and try again.",
                     "fr": "Trop de demandes. Veuillez attendre quelques minutes et réessayer."},
    "amount_range": {"en": "Please enter an amount {range}.", "fr": "Veuillez saisir un montant {range}."},
    "demo_disabled": {"en": "Payments are not available yet. Online payment will be added later.",
                      "fr": "Les paiements ne sont pas encore disponibles. Le paiement en ligne sera ajouté plus tard."},
    "not_found": {"en": "We could not find that item.", "fr": "Élément introuvable."},
    "password_short": {"en": "Password must be at least 8 characters.",
                       "fr": "Le mot de passe doit contenir au moins 8 caractères."},
    "wrong_password": {"en": "Your current password is not correct.",
                       "fr": "Votre mot de passe actuel est incorrect."},
    "email_failed": {"en": "We could not send the email right now. Please try again in a few minutes.",
                     "fr": "Impossible d'envoyer le courriel pour le moment. Veuillez réessayer dans quelques minutes."},
    "resend_limit": {"en": "You have resent this email several times. Please try again in an hour.",
                     "fr": "Vous avez renvoyé ce courriel plusieurs fois. Veuillez réessayer dans une heure."},
    "not_authenticated": {"en": "Please sign in to continue.", "fr": "Veuillez vous connecter pour continuer."},
    "forbidden": {"en": "You do not have access to this page.", "fr": "Vous n'avez pas accès à cette page."},
    "already_paid": {"en": "This payment has already been processed.", "fr": "Ce paiement a déjà été traité."},
    "google_failed": {"en": "Google sign-in did not complete. Please try again.",
                      "fr": "La connexion Google n'a pas abouti. Veuillez réessayer."},
}


def lang_of(request: Request) -> str:
    lang = (request.headers.get("X-Lang") or "en")[:2].lower()
    return lang if lang in ("en", "fr") else "en"


def msg(request: Request, key: str, **kw) -> str:
    return MSG[key][lang_of(request)].format(**kw)


def fail(request: Request, key: str, status: int, **kw):
    raise HTTPException(status_code=status, detail=msg(request, key, **kw))


# ---------- request helpers ----------
def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


_buckets: dict = {}


def rate_limit(key: str, limit: int, window_s: int) -> bool:
    t = time.monotonic()
    hits = [x for x in _buckets.get(key, []) if t - x < window_s]
    if len(hits) >= limit:
        _buckets[key] = hits
        return False
    hits.append(t)
    _buckets[key] = hits
    return True


async def verify_turnstile(token: str, ip: str) -> bool:
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                             data={"secret": TURNSTILE_SECRET, "response": token, "remoteip": ip})
            return bool(r.json().get("success"))
    except Exception as e:
        logger.warning("Turnstile verification error: %s", type(e).__name__)
        return False


# ---------- sessions ----------
def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": now() + timedelta(days=SESSION_DAYS), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def set_session(response, user_id: str):
    response.set_cookie("access_token", create_token(user_id), httponly=True, secure=True,
                        samesite="none", max_age=SESSION_DAYS * 86400, path="/")


def public_user(u: dict) -> dict:
    return {
        "id": u["id"], "email": u["email"], "name": u.get("name") or "",
        "is_admin": bool(u.get("is_admin")), "auth_method": u.get("auth_method"),
        "password_set": bool(u.get("password_set")), "lang": u.get("lang") or "en",
        "created_at": ser(u.get("created_at")),
    }


async def get_optional_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else None
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != "access":
        return None
    return await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})


async def get_current_user(request: Request):
    user = await get_optional_user(request)
    if not user:
        fail(request, "not_authenticated", 401)
    return user


async def require_admin(request: Request, user=Depends(get_current_user)):
    if not user.get("is_admin"):
        fail(request, "forbidden", 403)
    return user


async def create_user(email: str, *, auth_method: str, name: str = "", password_hash=None, lang="en"):
    doc = {
        "id": new_id(), "email": email, "name": name, "password_hash": password_hash,
        "password_set": password_hash is not None, "auth_method": auth_method,
        "is_admin": email in ADMIN_EMAILS, "lang": lang, "created_at": now(),
    }
    await db.users.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------- config / content ----------
def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


async def get_config() -> dict:
    doc = await db.app_config.find_one({"_id": "app"}, {"_id": 0}) or {}
    return _merge(DEFAULT_CONFIG, doc)


async def get_content() -> dict:
    doc = await db.landing_content.find_one({"_id": "landing"}, {"_id": 0}) or {}
    return {
        "en": doc.get("en") or copy.deepcopy(DEFAULT_CONTENT["en"]),
        "fr": doc.get("fr") or copy.deepcopy(DEFAULT_CONTENT["fr"]),
        "updated_at": ser(doc.get("updated_at")), "updated_by": doc.get("updated_by"),
    }


def amount_range_text(cfg: dict, lang: str) -> str:
    mn, mx = cfg["min_amount"], cfg["max_amount"]
    if mx:
        return f"between ${mn:g} and ${mx:g} CAD" if lang == "en" else f"entre {mn:g} $ et {mx:g} $ CAD"
    return f"of at least ${mn:g} CAD" if lang == "en" else f"d'au moins {mn:g} $ CAD"
