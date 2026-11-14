from typing import Optional

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from core import (db, now, new_id, ser, to_cents, dollars, generate_code, get_current_user, get_config,
                  get_content, fail, lang_of, rate_limit, amount_range_text, client_ip, DEMO_PAYMENTS_ENABLED)
from emailer import spawn, deliver_gift_email

router = APIRouter(prefix="/api")


class CheckoutIn(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    message: Optional[str] = Field(default=None, max_length=500)
    recipient_first_name: Optional[str] = Field(default=None, max_length=60)


class TrackIn(BaseModel):
    path: str = Field(max_length=500)
    referrer: Optional[str] = Field(default=None, max_length=500)


def demo_enabled(cfg: dict) -> bool:
    return DEMO_PAYMENTS_ENABLED and cfg["payment_mode"] == "placeholder"


def display_status(g: dict) -> str:
    if g["status"] == "revoked":
        return "revoked"
    if g["status"] == "used_up" or g["balance_cents"] <= 0:
        return "used_up"
    return "partly_used" if g["balance_cents"] < g["amount_cents"] else "active"


def gift_public(g: dict, redemptions: list) -> dict:
    return {
        "id": g["id"], "code": g["code"], "amount": dollars(g["amount_cents"]), "balance": dollars(g["balance_cents"]),
        "currency": g["currency"], "message": g.get("message"), "recipient_first_name": g.get("recipient_first_name"),
        "status": g["status"], "display_status": display_status(g), "locked": bool(g.get("locked")),
        "demo": bool(g.get("demo")), "email_status": g.get("email_status"),
        "created_at": ser(g["created_at"]), "last_redeemed_at": ser(g.get("last_redeemed_at")),
        "redemptions": [{
            "id": r["id"], "course_name": r["course_name"], "amount_used": dollars(r["amount_used_cents"]),
            "balance_after": dollars(r.get("balance_after_cents") or 0), "created_at": ser(r["created_at"]),
        } for r in redemptions if r.get("state") == "done"],
    }


@router.get("/public/config")
async def public_config():
    cfg = await get_config()
    return {
        "min_amount": cfg["min_amount"], "max_amount": cfg["max_amount"], "texts": cfg["texts"],
        "payment_mode": cfg["payment_mode"], "demo_payments": demo_enabled(cfg), "features": cfg["features"],
    }


@router.get("/content")
async def public_content():
    return await get_content()


@router.post("/track")
async def track(body: TrackIn, request: Request):
    if rate_limit(f"track:{client_ip(request)}", 120, 60):
        await db.request_logs.insert_one({
            "id": new_id(), "ts": now(), "ip": client_ip(request), "method": "VIEW", "kind": "page",
            "path": body.path, "referrer": body.referrer or "", "status": 200,
            "user_agent": (request.headers.get("user-agent") or "")[:300],
        })
    return {"ok": True}


@router.post("/gifts/checkout")
async def checkout(body: CheckoutIn, request: Request, user=Depends(get_current_user)):
    cfg = await get_config()
    amount = round(body.amount, 2)
    mn, mx = cfg["min_amount"], cfg["max_amount"]
    if amount < mn or (mx and amount > mx):
        fail(request, "amount_range", 400, range=amount_range_text(cfg, lang_of(request)))
    payment = {
        "id": new_id(), "gift_giver_id": user["id"], "gift_id": None, "amount_cents": to_cents(amount),
        "currency": "CAD", "provider": "placeholder" if cfg["payment_mode"] == "placeholder" else cfg["payment_mode"],
        "provider_ref": None, "status": "pending", "created_at": now(),
        "draft": {"message": (body.message or "").strip() or None,
                  "recipient_first_name": (body.recipient_first_name or "").strip() or None,
                  "lang": lang_of(request)},
    }
    await db.payments.insert_one(payment)
    return {"payment_id": payment["id"], "amount": amount, "currency": "CAD", "demo_payments": demo_enabled(cfg)}


async def fulfill_payment(payment: dict, demo: bool) -> dict:
    # Only call after the payment is verified (demo confirm, or a verified provider webhook later).
    draft = payment["draft"]
    for _ in range(10):
        code = generate_code()
        gift = {
            "id": new_id(), "code": code, "code_prefix": code[:8], "gift_giver_id": payment["gift_giver_id"],
            "amount_cents": payment["amount_cents"], "balance_cents": payment["amount_cents"], "currency": payment["currency"],
            "message": draft.get("message"), "recipient_first_name": draft.get("recipient_first_name"),
            "status": "active", "wrong_entries": 0, "locked": False, "demo": demo, "lang": draft.get("lang"),
            "email_status": "pending", "email_attempts": 0, "payment_id": payment["id"],
            "created_at": now(), "last_redeemed_at": None,
        }
        try:
            await db.gifts.insert_one(gift)
            break
        except DuplicateKeyError:
            continue
    gift.pop("_id", None)
    await db.payments.update_one({"id": payment["id"]}, {"$set": {"gift_id": gift["id"]}})
    spawn(deliver_gift_email(gift["id"]))
    return gift


@router.post("/payments/{payment_id}/demo-confirm")
async def demo_confirm(payment_id: str, request: Request, user=Depends(get_current_user)):
    cfg = await get_config()
    if not demo_enabled(cfg):
        fail(request, "demo_disabled", 403)
    payment = await db.payments.find_one_and_update(
        {"id": payment_id, "gift_giver_id": user["id"], "status": "pending"},
        {"$set": {"status": "processed", "provider_ref": f"DEMO-{new_id()[:10].upper()}", "processed_at": now()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER,
    )
    if not payment:
        existing = await db.payments.find_one({"id": payment_id, "gift_giver_id": user["id"]}, {"_id": 0})
        fail(request, "already_paid" if existing else "not_found", 409 if existing else 404)
    gift = await fulfill_payment(payment, demo=True)
    return gift_public(gift, [])


@router.post("/payments/webhook/{provider}")
async def payment_webhook(provider: str):
    # Placeholder: a real provider (e.g. Zeffy) must verify the event signature here, then call fulfill_payment.
    return {"ok": False, "detail": "No live payment provider is configured yet."}


@router.get("/gifts/mine")
async def my_gifts(user=Depends(get_current_user)):
    gifts = await db.gifts.find({"gift_giver_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    ids = [g["id"] for g in gifts]
    reds = await db.redemptions.find({"gift_id": {"$in": ids}}, {"_id": 0}).sort("created_at", 1).to_list(5000)
    by_gift = {}
    for r in reds:
        by_gift.setdefault(r["gift_id"], []).append(r)
    return [gift_public(g, by_gift.get(g["id"], [])) for g in gifts]


@router.get("/gifts/mine/{gift_id}")
async def my_gift(gift_id: str, request: Request, user=Depends(get_current_user)):
    g = await db.gifts.find_one({"id": gift_id, "gift_giver_id": user["id"]}, {"_id": 0})
    if not g:
        fail(request, "not_found", 404)
    reds = await db.redemptions.find({"gift_id": gift_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return gift_public(g, reds)


@router.post("/gifts/mine/{gift_id}/resend-email")
async def resend_gift_email(gift_id: str, request: Request, user=Depends(get_current_user)):
    g = await db.gifts.find_one({"id": gift_id, "gift_giver_id": user["id"]}, {"_id": 0, "id": 1})
    if not g:
        fail(request, "not_found", 404)
    if not rate_limit(f"resend:{gift_id}", 3, 3600):
        fail(request, "resend_limit", 429)
    ok = await deliver_gift_email(gift_id)
    if not ok:
        fail(request, "email_failed", 503)
    return {"sent": True}
