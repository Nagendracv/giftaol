import os
import re
import asyncio
import logging
from contextlib import suppress

from core import db, client, now, new_id, client_ip, hash_password, ADMIN_EMAILS, logger
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from pymongo import ASCENDING, DESCENDING, IndexModel

import routes_auth
import routes_gifts
import routes_harmony
import routes_admin
from emailer import spawn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

INDEXES: dict[str, list[IndexModel]] = {
    "users": [IndexModel([("email", ASCENDING)], name="email", unique=True),
              IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "email_verifications": [IndexModel([("email", ASCENDING)], name="email", unique=True)],
    "code_request_log": [IndexModel([("email", ASCENDING), ("requested_at", DESCENDING)], name="email_time"),
                         IndexModel([("requested_at", ASCENDING)], name="ttl", expireAfterSeconds=172800)],
    "login_attempts": [IndexModel([("identifier", ASCENDING)], name="identifier", unique=True),
                       IndexModel([("last_at", ASCENDING)], name="ttl", expireAfterSeconds=86400)],
    "gifts": [IndexModel([("id", ASCENDING)], name="id", unique=True),
              IndexModel([("code", ASCENDING)], name="code", unique=True),
              IndexModel([("code_prefix", ASCENDING)], name="code_prefix"),
              IndexModel([("gift_giver_id", ASCENDING), ("created_at", DESCENDING)], name="giver_time"),
              IndexModel([("locked", ASCENDING)], name="locked")],
    "redemptions": [IndexModel([("harmony_ref", ASCENDING)], name="harmony_ref", unique=True),
                    IndexModel([("gift_id", ASCENDING), ("created_at", ASCENDING)], name="gift_time")],
    "payments": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "harmony_keys": [IndexModel([("key_hash", ASCENDING)], name="key_hash"),
                     IndexModel([("revoked", ASCENDING), ("created_at", DESCENDING)], name="active")],
    "harmony_calls": [IndexModel([("ts", ASCENDING)], name="ttl", expireAfterSeconds=7776000)],
    "request_logs": [IndexModel([("ts", ASCENDING)], name="ttl", expireAfterSeconds=2592000),
                     IndexModel([("status", ASCENDING)], name="status")],
    "landing_content_versions": [IndexModel([("archived_at", DESCENDING)], name="archived")],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)


async def seed_admins() -> None:
    if ADMIN_EMAILS:
        await db.users.update_many({"email": {"$in": ADMIN_EMAILS}}, {"$set": {"is_admin": True}})
    email, pw = os.environ.get("ADMIN_EMAIL", "").lower(), os.environ.get("ADMIN_PASSWORD")
    if email and pw and not await db.users.find_one({"email": email}, {"_id": 1}):
        await db.users.insert_one({"id": new_id(), "email": email, "name": "Admin", "password_hash": hash_password(pw),
                                   "password_set": True, "auth_method": "email", "is_admin": True, "lang": "en", "created_at": now()})


app = FastAPI()

CODE_IN_PATH = re.compile(r"^(/api/gifts/)(?!mine|checkout)([A-Za-z0-9-]{4})[A-Za-z0-9-]*")


async def _log_request(doc: dict):
    with suppress(Exception):
        await db.request_logs.insert_one(doc)


@app.middleware("http")
async def hack_monitor(request: Request, call_next):
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        path = request.url.path
        if request.method != "OPTIONS" and path != "/api/track":
            path = CODE_IN_PATH.sub(r"\1\2-****", path)
            spawn(_log_request({
                "id": new_id(), "ts": now(), "ip": client_ip(request), "method": request.method, "kind": "api",
                "path": path, "referrer": (request.headers.get("referer") or "")[:500], "status": status,
                "user_agent": (request.headers.get("user-agent") or "")[:300],
            }))


app.include_router(routes_auth.router)
app.include_router(routes_gifts.router)
app.include_router(routes_admin.router)
app.include_router(routes_harmony.router)


@app.get("/api/")
async def root():
    return {"message": "giftaol.ca API"}


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    app.state.index_task = asyncio.create_task(ensure_indexes())
    await seed_admins()


@app.on_event("shutdown")
async def shutdown():
    app.state.index_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.index_task
    client.close()
