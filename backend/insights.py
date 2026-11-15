"""Visit insights: tab views and course interactions per city site."""

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request, Response

from courses import find_course, haversine_km
from db import db
from home_view import DISTANCES, courses_for
from roles import require_role

logger = logging.getLogger("citysites")
router = APIRouter(prefix="/api")
COURSE_EVENTS = ("course_open", "register_click", "calendar_add", "share", "reminder_signup")
EVENTS_PER_MINUTE = 30
BOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|curl|wget|python-requests", re.I)
_recent: dict[str, list] = {}


async def record_event(city_id: str, kind: str, **fields) -> None:
    try:
        await db.insight_events.insert_one({"ts": datetime.now(timezone.utc), "city_id": city_id, "kind": kind, **fields})
    except Exception as exc:
        logger.error("Could not record insight event: %s", exc)


async def record_course_event(city_id: str, kind: str, course: dict) -> None:
    await record_event(city_id, kind, course_id=course["id"], course_title=course["title"],
                       program=course["program"], course_start=course["start"].isoformat())


@router.post("/insights/event", status_code=204)
async def course_event(request: Request):
    """Beacon from the home page (sendBeacon posts text/plain JSON)."""
    city = request.state.city
    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError:
        return Response(status_code=204)
    if not city or body.get("kind") not in COURSE_EVENTS or not isinstance(body.get("courseId"), str):
        return Response(status_code=204)
    from server import client_ip  # avoid a circular import at load time
    if not _allow(client_ip(request)):
        return Response(status_code=204)
    course = find_course(await courses_for("en"), body["courseId"])
    if course and _in_area(course, city):
        await record_course_event(city["cityId"], body["kind"], course)
    return Response(status_code=204)


def _in_area(course: dict, city: dict) -> bool:
    """Only count courses this site can list (online ones, or in person within the widest distance choice)."""
    if course["online"]:
        return True
    if city.get("latitude") is None or course["lat"] is None:
        return False
    return haversine_km(city["latitude"], city["longitude"], course["lat"], course["lon"]) <= max(DISTANCES)


def _allow(ip: str) -> bool:
    """At most EVENTS_PER_MINUTE beacons per IP per minute (in memory)."""
    now = time.monotonic()
    recent = [t for t in _recent.get(ip, []) if now - t < 60]
    if len(_recent) > 10000:
        _recent.clear()
    _recent[ip] = recent + [now]
    return len(recent) < EVENTS_PER_MINUTE


def is_bot(user_agent: str) -> bool:
    return bool(BOT_RE.search(user_agent or ""))


@router.get("/admin/insights")
async def insights(city: str | None = None, days: int = Query(30, ge=1, le=90),
                   admin: dict = Depends(require_role("admin"))):
    match = {"ts": {"$gte": datetime.now(timezone.utc) - timedelta(days=days)}}
    if city:
        match["city_id"] = city
    tabs = await db.insight_events.aggregate([
        {"$match": {**match, "kind": "tab_view"}},
        {"$group": {"_id": "$tab", "views": {"$sum": 1}}},
        {"$sort": {"views": -1}},
    ]).to_list(10)
    courses = await db.insight_events.aggregate([
        {"$match": {**match, "kind": {"$in": list(COURSE_EVENTS)}}},
        {"$group": {"_id": {"course": "$course_id", "kind": "$kind"}, "n": {"$sum": 1},
                    "title": {"$last": "$course_title"}, "program": {"$last": "$program"},
                    "start": {"$last": "$course_start"}, "city": {"$last": "$city_id"}}},
    ]).to_list(5000)
    by_course: dict = {}
    for row in courses:
        cid = row["_id"]["course"]
        item = by_course.setdefault(cid, {"courseId": cid, "title": row["title"], "program": row["program"],
                                          "start": row["start"], "cityId": row["city"], **{k: 0 for k in COURSE_EVENTS}})
        item[row["_id"]["kind"]] = row["n"]
    top = sorted(by_course.values(), key=lambda c: (c["course_open"], c["register_click"]), reverse=True)[:50]
    return {"days": days, "tabs": [{"tab": t["_id"], "views": t["views"]} for t in tabs], "courses": top}
