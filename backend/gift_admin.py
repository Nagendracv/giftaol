"""Gift code API for Harmony (lookup and redeem) and the admin screens (settings, codes, unlock)."""

import logging
import re
import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from db import db
from gift_emails import send_redemption
from gifts import BACKGROUND_DELAYS, CODE_LENGTH, send_with_retry, DEFAULT_SETTINGS, gift_settings, gift_view, normalize_code, now, redemptions_for, to_cents
from roles import require_role
from state import STATE

logger = logging.getLogger("citysites")
router = APIRouter(prefix="/api")
admin_only = Depends(require_role("admin"))
UNKNOWN_PER_IP_HOUR = 30
LOCKED = "This code is temporarily locked."


def _ip(request: Request) -> str:
    from server import client_ip
    return client_ip(request)


def _error(status: int, error: str, message: str) -> JSONResponse:
    return JSONResponse({"error": error, "message": message}, status_code=status)


async def _find(raw: str, request: Request):
    """Returns (gift, None) or (None, error response). Unknown codes are rate-limited per IP."""
    code = normalize_code(raw)
    gift = await db.gifts.find_one({"code": code}, {"_id": 0}) if len(code) == CODE_LENGTH else None
    if not gift:
        ip = _ip(request)
        if await db.gift_failed_lookups.count_documents({"ip": ip, "at": {"$gte": now() - timedelta(hours=1)}}) >= UNKNOWN_PER_IP_HOUR:
            return None, _error(429, "too_many_attempts", "Too many unknown codes from this address. Try again later.")
        await db.gift_failed_lookups.insert_one({"ip": ip, "at": now()})
        return None, _error(404, "not_found", "Code not found.")
    if gift.get("locked"):
        return None, _error(423, "locked", LOCKED)
    return gift, None


async def _wrong_entry(gift: dict) -> bool:
    """Counts a rejected use of this code; locks it at the admin-set cap. Returns True if now locked."""
    cap = (await gift_settings())["wrongEntryCap"]
    updated = await db.gifts.find_one_and_update({"id": gift["id"]}, {"$inc": {"wrong_entries": 1}},
                                                 projection={"_id": 0, "wrong_entries": 1}, return_document=ReturnDocument.AFTER)
    if updated["wrong_entries"] >= cap:
        await db.gifts.update_one({"id": gift["id"]}, {"$set": {"locked": True, "locked_at": now()}})
        return True
    return False


def _public(gift: dict) -> dict:
    return {"code": gift_view(gift)["code"], "status": gift["status"], "balance": gift["balance_cents"] / 100,
            "amount": gift["amount_cents"] / 100, "currency": gift["currency"]}


@router.get("/gift-codes/{code}")
async def lookup(code: str, request: Request):
    gift, error = await _find(code, request)
    return error or _public(gift)


class RedeemIn(BaseModel):
    amount: float | str
    courseName: str = Field(min_length=1, max_length=200)
    courseReference: str = Field(min_length=1, max_length=100)


async def _notify(gift: dict, redemption: dict) -> None:
    city = STATE.config.cities.get(gift["city_id"])
    texts = STATE.texts.bundle(gift["locale"])
    ok = await send_with_retry(lambda: send_redemption(gift, redemption, city, texts), BACKGROUND_DELAYS,
                               f"Redemption email {redemption['id']}")
    await db.gift_redemptions.update_one({"id": redemption["id"]}, {"$set": {"email_status": "sent" if ok else "failed"}})


@router.post("/gift-codes/{code}/redeem")
async def redeem(code: str, body: RedeemIn, request: Request, background: BackgroundTasks):
    gift, error = await _find(code, request)
    if error:
        return error
    ref = body.courseReference.strip()
    previous = await db.gift_redemptions.find_one({"gift_id": gift["id"], "course_reference": ref}, {"_id": 0})
    if previous:  # same course reference reported again: return the earlier result, never deduct twice
        return {**_public(gift), "amountUsed": previous["amount_cents"] / 100, "redemptionId": previous["id"], "duplicate": True}
    cents = to_cents(body.amount)
    reason = ("revoked" if gift["status"] == "revoked" else "used_up" if gift["status"] == "used_up"
              else "invalid_amount" if cents is None else "over_balance" if cents > gift["balance_cents"] else None)
    if reason:
        locked = await _wrong_entry(gift)
        messages = {"revoked": "This code has been revoked.", "used_up": "This code has been fully used.",
                    "invalid_amount": "The amount must be greater than 0.",
                    "over_balance": f"The amount is more than the balance of {gift['balance_cents'] / 100:.2f} {gift['currency']}."}
        return _error(423, "locked", LOCKED) if locked else _error(409 if reason != "invalid_amount" else 400, reason, messages[reason])
    updated = await db.gifts.find_one_and_update(
        {"id": gift["id"], "status": "active", "locked": False, "balance_cents": {"$gte": cents}},
        {"$inc": {"balance_cents": -cents}, "$set": {"last_redeemed_at": now()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not updated:
        return _error(409, "over_balance", "The balance changed. Look up the code again.")
    if updated["balance_cents"] == 0:
        await db.gifts.update_one({"id": gift["id"]}, {"$set": {"status": "used_up"}})
        updated["status"] = "used_up"
    redemption = {"id": str(uuid.uuid4()), "gift_id": gift["id"], "code": gift["code"], "course_name": body.courseName.strip(),
                  "course_reference": ref, "amount_cents": cents, "balance_after_cents": updated["balance_cents"],
                  "created_at": now(), "email_status": "pending"}
    await db.gift_redemptions.insert_one(dict(redemption))
    background.add_task(_notify, updated, redemption)
    return {**_public(updated), "amountUsed": cents / 100, "redemptionId": redemption["id"], "duplicate": False}


# --- Admin ---------------------------------------------------------------------

class SettingsIn(BaseModel):
    minAmount: float = Field(gt=0, le=100000)
    maxAmount: float | None = Field(default=None, gt=0, le=100000)
    wrongEntryCap: int = Field(ge=1, le=100)
    presets: list[float] = Field(default_factory=list, max_length=8)


@router.get("/admin/gift-settings")
async def get_settings(admin: dict = admin_only):
    return {**(await gift_settings()), "defaults": DEFAULT_SETTINGS}


@router.put("/admin/gift-settings")
async def put_settings(body: SettingsIn, admin: dict = admin_only):
    if body.maxAmount is not None and body.maxAmount < body.minAmount:
        raise HTTPException(status_code=422, detail="The maximum must be at least the minimum")
    data = {**body.model_dump(), "presets": sorted({round(p, 2) for p in body.presets if p > 0})}
    await db.gift_settings.replace_one({"_id": "current"}, {**data, "updated_by": admin.get("email"), "updated_at": now()}, upsert=True)
    return await get_settings(admin)


@router.get("/admin/gifts")
async def list_gifts(q: str | None = None, page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100), admin: dict = admin_only):
    query: dict = {}
    if q and q.strip():
        code = normalize_code(q)
        ors = [{"gift_giver_email": {"$regex": re.escape(q.strip().lower())}}]
        if code:
            ors.append({"code": {"$regex": re.escape(code)}})
        query = {"$or": ors}
    total = await db.gifts.count_documents(query)
    gifts = await db.gifts.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * size).limit(size).to_list(size)
    grouped = await redemptions_for([g["id"] for g in gifts])
    items = [{**gift_view(g, grouped[g["id"]]), "wrongEntries": g.get("wrong_entries", 0), "locked": g.get("locked", False),
              "rawStatus": g["status"]} for g in gifts]
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/admin/gifts/{gift_id}/unlock")
async def unlock(gift_id: str, admin: dict = admin_only):
    r = await db.gifts.update_one({"id": gift_id}, {"$set": {"locked": False, "wrong_entries": 0, "unlocked_by": admin.get("email")}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Gift not found")
    return {"ok": True}


@router.post("/admin/gifts/{gift_id}/revoke")
async def revoke(gift_id: str, admin: dict = admin_only):
    r = await db.gifts.update_one({"id": gift_id, "status": "active"}, {"$set": {"status": "revoked", "revoked_by": admin.get("email")}})
    if not r.matched_count:
        raise HTTPException(status_code=409, detail="Only active codes can be revoked")
    return {"ok": True}
