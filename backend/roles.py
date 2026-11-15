import os
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo import ReturnDocument
from starlette.concurrency import run_in_threadpool

from clerk_auth import require_user
from db import db

router = APIRouter(prefix="/api")

# The role list is code, so every publish ships it to Live. Highest first; keep `admin`.
ROLES = ["admin", "member"]
DEFAULT_ROLE = "member"
RETIRED_ROLES = {}  # removed role -> role its people move to; keep entries
RANK = {r: len(ROLES) - i for i, r in enumerate(ROLES)}

# Which Clerk instance signed the person in: the first publish copies preview users into Live's database.
ENV = "live" if os.environ.get("CLERK_PUBLISHABLE_KEY", "").startswith("pk_live_") else "preview"
IN_ENV = {"env": {"$in": [ENV, None]}}


def effective_role(role) -> str:
    role = RETIRED_ROLES.get(role, role)
    return role if role in ROLES else DEFAULT_ROLE


async def move_retired_roles():
    for old, new in RETIRED_ROLES.items():
        await db.users.update_many({"role": old}, {"$set": {"role": new}})


def _clerk_user(user_id: str) -> dict:  # one Clerk lookup on first sign-in, never per request
    r = requests.get(f"https://api.clerk.com/v1/users/{user_id}", timeout=10,
                     headers={"Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}", "User-Agent": "emergent-app"})
    r.raise_for_status()
    return r.json()


def _primary_email(user: dict) -> str:
    emails = user.get("email_addresses") or []
    primary = next((e for e in emails if e["id"] == user.get("primary_email_address_id")), emails[0] if emails else None)
    return primary["email_address"] if primary else ""


def _is_admin_email(user: dict) -> bool:
    admins = {e.strip().lower() for e in os.environ.get("ADMIN_EMAIL", "").split(",") if e.strip()}
    return any(e["email_address"].lower() in admins and (e.get("verification") or {}).get("status") == "verified"
               for e in user.get("email_addresses") or [])


async def current_member(user: dict = Depends(require_user)) -> dict:
    uid = user["user_id"]
    member = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if member is None or not member.get("role") or not member.get("email"):
        clerk_user = await run_in_threadpool(_clerk_user, uid)
        if member is None or not member.get("role"):
            role = "admin" if _is_admin_email(clerk_user) else DEFAULT_ROLE
            await db.users.update_one({"user_id": uid, "role": {"$in": [None, ""]}}, {"$set": {"role": role}})
            member = await db.users.find_one_and_update(
                {"user_id": uid},
                {"$setOnInsert": {"user_id": uid, "role": role, "created_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True, projection={"_id": 0}, return_document=ReturnDocument.AFTER)
        member["email"] = _primary_email(clerk_user)
        await db.users.update_one({"user_id": uid}, {"$set": {"email": member["email"]}})
    if member.get("env") != ENV:
        await db.users.update_one({"user_id": uid}, {"$set": {"env": ENV}})
    return {**member, "env": ENV, "role": effective_role(member["role"])}


def require_role(*roles: str):
    async def check(member: dict = Depends(current_member)) -> dict:
        if member["role"] not in roles:
            raise HTTPException(status_code=403, detail="Not allowed")
        return member
    return check


@router.get("/me")
async def me(member: dict = Depends(current_member)):
    return {"user_id": member["user_id"], "email": member.get("email", ""), "role": member["role"]}


@router.get("/users")
async def list_users(admin: dict = Depends(require_role("admin"))):
    people = await db.users.find(IN_ENV, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return {"roles": [r for r in ROLES if RANK[r] <= RANK[admin["role"]]],
            "users": [{**p, "role": effective_role(p.get("role"))} for p in people]}


class RoleIn(BaseModel):
    role: str


@router.patch("/users/{user_id}/role")
async def set_role(user_id: str, body: RoleIn, admin: dict = Depends(require_role("admin"))):
    if body.role not in ROLES or RANK[body.role] > RANK[admin["role"]]:
        raise HTTPException(status_code=403, detail="Not allowed")
    target = await db.users.find_one({"user_id": user_id, **IN_ENV}, {"_id": 0})
    if target is None:
        raise HTTPException(status_code=404, detail="Not found")
    if (effective_role(target.get("role")) == "admin" and body.role != "admin"
            and await db.users.count_documents({"role": "admin", **IN_ENV}) <= 1):
        raise HTTPException(status_code=409, detail="Keep at least one admin")
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": body.role}})
    return {"user_id": user_id, "role": body.role}
