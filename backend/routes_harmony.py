from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from core import db, now, new_id, hash_secret, normalize_code, mask_code, to_cents, dollars, get_config
from emailer import spawn, deliver_redemption_email

router = APIRouter(prefix="/api")
LOCKED = "This code is temporarily locked."


class RedeemIn(BaseModel):
    amount_used: float = Field(gt=0, le=1_000_000)
    course_name: str = Field(min_length=1, max_length=200)
    harmony_ref: str = Field(min_length=1, max_length=200)


async def _log(endpoint: str, status: int, code: str):
    await db.harmony_calls.insert_one({"id": new_id(), "ts": now(), "endpoint": endpoint, "status": status, "code": mask_code(code)})


async def _check_key(request: Request):
    key = request.headers.get("X-Harmony-Key")
    if not key or not await db.harmony_keys.find_one({"key_hash": hash_secret(key), "revoked": False}, {"_id": 1}):
        raise HTTPException(status_code=401, detail="Missing or invalid Harmony API key.")


async def _find_gift(code: str) -> dict:
    gift = await db.gifts.find_one({"code": code}, {"_id": 0}) if len(code) == 16 else None
    if gift:
        if gift.get("locked"):
            raise HTTPException(status_code=423, detail=LOCKED)
        if gift.get("wrong_entries"):
            await db.gifts.update_one({"id": gift["id"]}, {"$set": {"wrong_entries": 0}})
        return gift
    # Wrong entry: count it against the gift whose first 8 characters match (likely mistyped or guessed).
    if len(code) >= 8:
        cfg = await get_config()
        near = await db.gifts.find_one_and_update(
            {"code_prefix": code[:8]}, {"$inc": {"wrong_entries": 1}},
            projection={"_id": 0, "id": 1, "wrong_entries": 1}, return_document=ReturnDocument.AFTER)
        if near and near["wrong_entries"] >= int(cfg["wrong_entry_cap"]):
            await db.gifts.update_one({"id": near["id"]}, {"$set": {"locked": True, "locked_at": now()}})
    raise HTTPException(status_code=404, detail="Gift code not found.")


def _state(g: dict) -> dict:
    return {"status": g["status"], "balance": dollars(g["balance_cents"]), "currency": g["currency"]}


async def _run(endpoint: str, code: str, fn):
    try:
        result = await fn()
        await _log(endpoint, 200, code)
        return result
    except HTTPException as e:
        await _log(endpoint, e.status_code, code)
        raise


@router.get("/gifts/{raw_code}")
async def harmony_lookup(raw_code: str, request: Request):
    code = normalize_code(raw_code)

    async def go():
        await _check_key(request)
        return _state(await _find_gift(code))
    return await _run("lookup", code, go)


@router.post("/gifts/{raw_code}/redeem")
async def harmony_redeem(raw_code: str, body: RedeemIn, request: Request):
    code = normalize_code(raw_code)

    async def go():
        await _check_key(request)
        gift = await _find_gift(code)
        amt = to_cents(body.amount_used)
        prior = await db.redemptions.find_one({"harmony_ref": body.harmony_ref}, {"_id": 0})
        if prior:
            return await _replay(prior, gift)
        if gift["status"] != "active" or gift["balance_cents"] <= 0:
            raise HTTPException(status_code=409, detail=f"Code cannot be redeemed (status: {gift['status']}).")
        if amt > gift["balance_cents"]:
            raise HTTPException(status_code=409, detail="Amount used is greater than the remaining balance.")
        red = {"id": new_id(), "gift_id": gift["id"], "harmony_ref": body.harmony_ref, "course_name": body.course_name.strip(),
               "amount_used_cents": amt, "balance_after_cents": None, "state": "pending", "created_at": now()}
        try:
            await db.redemptions.insert_one(red)
        except DuplicateKeyError:
            return await _replay(await db.redemptions.find_one({"harmony_ref": body.harmony_ref}, {"_id": 0}), gift)
        updated = await db.gifts.find_one_and_update(
            {"id": gift["id"], "status": "active", "locked": False, "balance_cents": {"$gte": amt}},
            {"$inc": {"balance_cents": -amt}, "$set": {"last_redeemed_at": now()}},
            projection={"_id": 0}, return_document=ReturnDocument.AFTER)
        if not updated:
            await db.redemptions.delete_one({"id": red["id"]})
            raise HTTPException(status_code=409, detail="Amount used is greater than the remaining balance.")
        if updated["balance_cents"] <= 0:
            await db.gifts.update_one({"id": gift["id"]}, {"$set": {"status": "used_up"}})
            updated["status"] = "used_up"
        await db.redemptions.update_one({"id": red["id"]}, {"$set": {"balance_after_cents": updated["balance_cents"], "state": "done"}})
        spawn(deliver_redemption_email(gift["id"], red["id"]))
        return {**_state(updated), "amount_used": dollars(amt), "harmony_ref": body.harmony_ref, "idempotent_replay": False}
    return await _run("redeem", code, go)


async def _replay(prior: dict, gift: dict):
    if prior["gift_id"] != gift["id"]:
        raise HTTPException(status_code=409, detail="This Harmony reference was already used with another code.")
    current = await db.gifts.find_one({"id": gift["id"]}, {"_id": 0})
    return {**_state(current), "amount_used": dollars(prior["amount_used_cents"]),
            "harmony_ref": prior["harmony_ref"], "idempotent_replay": True}
