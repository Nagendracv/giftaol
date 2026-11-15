import copy
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from db import db
from roles import require_role
from site_config import ConfigError, load_config_file, timezones, validate_config
from state import STATE
from storage import APP_NAME, get_object, put_object

logger = logging.getLogger("citysites")
router = APIRouter(prefix="/api")
admin_only = Depends(require_role("admin"))

LOGO_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg", "image/gif": "gif"}
MAX_LOGO_BYTES = 2 * 1024 * 1024
_logo_cache: dict[str, tuple[bytes, str]] = {}


def _available_locales() -> set:
    return set(STATE.texts.files)


async def load_admin_state() -> None:
    """Admin-saved config (if any) takes over from the file; text overrides layer on resource files."""
    doc = await db.site_config.find_one({"_id": "current"})
    if doc:
        try:
            STATE.config = validate_config(doc["config"], _available_locales())
            STATE.source = "admin"
        except ConfigError as exc:
            logger.error("Saved admin site configuration is invalid; using the file instead. %s", exc)
    overrides: dict = {}
    async for o in db.text_overrides.find({}, {"_id": 0}):
        overrides.setdefault(o["locale"], {})[o["key"]] = o["value"]
    STATE.texts.overrides = overrides


async def _save_config(raw: dict, admin: dict) -> None:
    try:
        config = validate_config(raw, _available_locales())
    except ConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.site_config.replace_one(
        {"_id": "current"},
        {"config": raw, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")},
        upsert=True)
    STATE.config, STATE.source = config, "admin"


def _config_payload() -> dict:
    return {"source": STATE.source, "config": STATE.config.raw, "locales": list(STATE.config.locales),
            "availableLocales": sorted(_available_locales())}


@router.get("/admin/config")
async def get_config(admin: dict = admin_only):
    return _config_payload()


@router.get("/admin/timezones")
async def get_timezones(admin: dict = admin_only):
    return sorted(timezones())


@router.put("/admin/config")
async def put_config(raw: dict = Body(...), admin: dict = admin_only):
    await _save_config(raw, admin)
    return _config_payload()


@router.delete("/admin/config")
async def reset_config(admin: dict = admin_only):
    try:
        config = validate_config(load_config_file(STATE.config_file), _available_locales())
    except ConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.site_config.delete_one({"_id": "current"})
    STATE.config, STATE.source = config, "file"
    return _config_payload()


@router.post("/admin/cities/{city_id}/logo")
async def upload_logo(city_id: str, file: UploadFile = File(...), admin: dict = admin_only):
    if city_id not in STATE.config.cities:
        raise HTTPException(status_code=404, detail="Unknown city")
    ext = LOGO_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="Logo must be a PNG, JPEG, WebP, SVG or GIF image")
    data = await file.read()
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Logo must be 2 MB or smaller")
    file_id = str(uuid.uuid4())
    result = await run_in_threadpool(put_object, f"{APP_NAME}/logos/{city_id}/{file_id}.{ext}", data, file.content_type)
    await db.files.insert_one({"id": file_id, "storage_path": result["path"], "original_filename": file.filename,
                               "content_type": file.content_type, "size": result.get("size", len(data)),
                               "city_id": city_id, "is_deleted": False,
                               "created_at": datetime.now(timezone.utc).isoformat()})
    raw = copy.deepcopy(STATE.config.raw)
    url = f"/api/logo/{file_id}"
    for city in raw["cities"]:
        if city.get("cityId") == city_id:
            city["logoUrl"] = url
    await _save_config(raw, admin)
    return {"logoUrl": url, **_config_payload()}


@router.get("/logo/{file_id}")
async def get_logo(file_id: str):
    if file_id not in _logo_cache:
        record = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Logo not found")
        data, _ = await run_in_threadpool(get_object, record["storage_path"])
        if len(_logo_cache) >= 50:
            _logo_cache.clear()
        _logo_cache[file_id] = (data, record["content_type"])
    data, content_type = _logo_cache[file_id]
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


@router.get("/admin/logs")
async def access_logs(city: str | None = None, host: str | None = None,
                      page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=200), admin: dict = admin_only):
    query: dict = {}
    if city:
        query["city_id"] = city
    if host:
        query["host"] = {"$regex": re.escape(host.strip().lower())}
    total = await db.access_logs.count_documents(query)
    docs = await db.access_logs.find(query, {"_id": 0}).sort("ts", -1).skip((page - 1) * size).limit(size).to_list(size)
    items = [{**d, "ts": d["ts"].replace(tzinfo=timezone.utc).isoformat()} for d in docs]
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/admin/texts")
async def get_texts(admin: dict = admin_only):
    STATE.texts.refresh()
    return {"locales": list(STATE.config.locales), "keys": list(STATE.texts.files["en"]),
            "files": STATE.texts.files, "overrides": STATE.texts.overrides}


class TextChange(BaseModel):
    locale: str
    key: str
    value: str | None = None


class TextChanges(BaseModel):
    changes: list[TextChange]


@router.put("/admin/texts")
async def put_texts(body: TextChanges, admin: dict = admin_only):
    keys = set(STATE.texts.files["en"])
    for c in body.changes:
        if c.locale not in STATE.texts.files or c.key not in keys:
            raise HTTPException(status_code=400, detail=f"Unknown text {c.locale}/{c.key}")
    for c in body.changes:
        file_value = STATE.texts.files[c.locale].get(c.key)
        bucket = STATE.texts.overrides.setdefault(c.locale, {})
        if not c.value or c.value == file_value:  # empty or same as the file -> back to the file text
            await db.text_overrides.delete_one({"locale": c.locale, "key": c.key})
            bucket.pop(c.key, None)
        else:
            await db.text_overrides.update_one(
                {"locale": c.locale, "key": c.key},
                {"$set": {"value": c.value, "updated_by": admin.get("email"),
                          "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
            bucket[c.key] = c.value
    return await get_texts(admin)
