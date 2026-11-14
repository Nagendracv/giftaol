import re
import secrets
from typing import Optional, List

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, Field

from core import (db, now, new_id, ser, hash_secret, require_admin, get_config, get_content, format_code,
                  dollars, DEMO_PAYMENTS_ENABLED)

router = APIRouter(prefix="/api/admin")


class Bilingual(BaseModel):
    en: str = Field(max_length=3000)
    fr: str = Field(max_length=3000)


class BilingualList(BaseModel):
    en: List[str] = Field(max_length=20)
    fr: List[str] = Field(max_length=20)


class TextsIn(BaseModel):
    explainer: Bilingual
    banner: Bilingual
    security: Bilingual
    next_steps: BilingualList
    payment_placeholder: Bilingual


class ConfigIn(BaseModel):
    min_amount: float = Field(gt=0, le=100000)
    max_amount: Optional[float] = Field(default=None, gt=0, le=1000000)
    payment_mode: str = Field(pattern="^(placeholder|zeffy|other)$")
    email_from_name: str = Field(default="", max_length=80)
    email_reply_to: str = Field(default="", max_length=200)
    code_request_limit: int = Field(ge=1, le=50)
    wrong_entry_cap: int = Field(ge=1, le=100)
    features: dict
    texts: TextsIn


class ContentIn(BaseModel):
    en: dict
    fr: dict


@router.get("/config")
async def admin_get_config(_=Depends(require_admin)):
    cfg = await get_config()
    cfg["demo_payments_env"] = DEMO_PAYMENTS_ENABLED
    return cfg


@router.put("/config")
async def admin_put_config(body: ConfigIn, admin=Depends(require_admin)):
    if body.max_amount is not None and body.max_amount < body.min_amount:
        raise HTTPException(status_code=400, detail="Maximum must be greater than or equal to the minimum.")
    data = body.model_dump()
    data["features"] = {k: bool(v) for k, v in body.features.items()}
    await db.app_config.update_one({"_id": "app"}, {"$set": {**data, "updated_at": now(), "updated_by": admin["email"]}}, upsert=True)
    return await admin_get_config(admin)


@router.get("/content")
async def admin_get_content(_=Depends(require_admin)):
    content = await get_content()
    content["versions"] = await db.landing_content_versions.count_documents({})
    return content


@router.put("/content")
async def admin_put_content(body: ContentIn, admin=Depends(require_admin)):
    if len(str(body.model_dump())) > 6_000_000:
        raise HTTPException(status_code=413, detail="Content is too large. Use image URLs or smaller images.")
    current = await db.landing_content.find_one({"_id": "landing"}, {"_id": 0})
    if current:
        await db.landing_content_versions.insert_one({"id": new_id(), **current, "archived_at": now()})
    await db.landing_content.update_one({"_id": "landing"}, {"$set": {"en": body.en, "fr": body.fr, "updated_at": now(), "updated_by": admin["email"]}}, upsert=True)
    return await admin_get_content(admin)


@router.post("/content/rollback")
async def admin_rollback(admin=Depends(require_admin)):
    prev = await db.landing_content_versions.find_one({}, {"_id": 0}, sort=[("archived_at", -1)])
    if not prev:
        raise HTTPException(status_code=404, detail="There is no previous version to restore.")
    await db.landing_content.update_one({"_id": "landing"}, {"$set": {"en": prev["en"], "fr": prev["fr"], "updated_at": now(), "updated_by": admin["email"]}}, upsert=True)
    await db.landing_content_versions.delete_one({"id": prev["id"]})
    return await admin_get_content(admin)


@router.get("/gifts/locked")
async def locked_gifts(_=Depends(require_admin)):
    gifts = await db.gifts.find({"locked": True}, {"_id": 0}).sort("locked_at", -1).to_list(200)
    return [{"id": g["id"], "code_masked": format_code(g["code"])[:9] + "-****-****", "amount": dollars(g["amount_cents"]),
             "balance": dollars(g["balance_cents"]), "wrong_entries": g.get("wrong_entries", 0),
             "locked_at": ser(g.get("locked_at"))} for g in gifts]


@router.post("/gifts/{gift_id}/unlock")
async def unlock_gift(gift_id: str, _=Depends(require_admin)):
    res = await db.gifts.update_one({"id": gift_id}, {"$set": {"locked": False, "wrong_entries": 0}, "$unset": {"locked_at": ""}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Gift not found.")
    return {"ok": True}


@router.get("/harmony-key")
async def harmony_key_status(_=Depends(require_admin)):
    key = await db.harmony_keys.find_one({"revoked": False}, {"_id": 0, "key_hash": 0}, sort=[("created_at", -1)])
    calls = await db.harmony_calls.find({}, {"_id": 0}).sort("ts", -1).to_list(25)
    return {
        "active": bool(key), "prefix": key["prefix"] if key else None, "created_at": ser(key["created_at"]) if key else None,
        "created_by": key.get("created_by") if key else None,
        "recent_calls": [{**c, "ts": ser(c["ts"])} for c in calls],
    }


@router.post("/harmony-key/rotate")
async def harmony_key_rotate(admin=Depends(require_admin)):
    raw = "hk_" + secrets.token_urlsafe(32)
    await db.harmony_keys.update_many({"revoked": False}, {"$set": {"revoked": True, "revoked_at": now()}})
    await db.harmony_keys.insert_one({"id": new_id(), "key_hash": hash_secret(raw), "prefix": raw[:7], "revoked": False,
                                      "created_at": now(), "created_by": admin["email"]})
    return {"key": raw, "prefix": raw[:7]}


@router.post("/harmony-key/revoke")
async def harmony_key_revoke(_=Depends(require_admin)):
    await db.harmony_keys.update_many({"revoked": False}, {"$set": {"revoked": True, "revoked_at": now()}})
    return {"ok": True}


@router.get("/request-logs")
async def request_logs(q: str = Query("", max_length=200), status: str = Query("all", max_length=10),
                       kind: str = Query("all", max_length=10), limit: int = Query(200, ge=1, le=1000),
                       _=Depends(require_admin)):
    flt = {}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        flt["$or"] = [{"ip": rx}, {"path": rx}, {"referrer": rx}, {"user_agent": rx}]
    if status == "2xx":
        flt["status"] = {"$gte": 200, "$lt": 300}
    elif status == "3xx":
        flt["status"] = {"$gte": 300, "$lt": 400}
    elif status == "4xx":
        flt["status"] = {"$gte": 400, "$lt": 500}
    elif status == "5xx":
        flt["status"] = {"$gte": 500}
    if kind in ("api", "page"):
        flt["kind"] = kind
    logs = await db.request_logs.find(flt, {"_id": 0}).sort("ts", -1).to_list(limit)
    total = await db.request_logs.count_documents({})
    errors = await db.request_logs.count_documents({"status": {"$gte": 400}})
    ips = len(await db.request_logs.distinct("ip"))
    return {"total": total, "errors": errors, "unique_ips": ips, "logs": [{**l, "ts": ser(l["ts"])} for l in logs]}
