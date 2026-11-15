"""Course reminder emails: double opt-in, sent about a day before the start, then deleted."""

import hmac
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from course_pages import fill, format_when
from courses import find_course
from db import db
from emailer import EMAIL_FROM_NAME, EmailUnavailable, send_email
from home_view import courses_for
from insights import record_course_event
from state import STATE

logger = logging.getLogger("citysites")
router = APIRouter(prefix="/api")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}$", re.I)
MAX_PER_EMAIL = 5
MAX_PER_IP_HOUR = 10
REMIND_BEFORE = timedelta(hours=24)


def site_url(host: str, path: str) -> str:
    return f"https://{host}{path}"


def sender(city: dict, texts: dict) -> str:
    return f'{EMAIL_FROM_NAME} {city["displayName"]}'  # e.g. "Art of Living Ottawa"


def _layout(texts: dict, city: dict, body: str) -> str:
    footer = escape(fill(texts["emailFooter"], site=sender(city, texts)))
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FAF9F6">'
            '<tr><td style="padding:32px 16px"><table role="presentation" width="100%" style="max-width:560px;margin:0 auto;'
            'background:#ffffff;border:1px solid #E7E5E4;border-radius:12px"><tr><td style="padding:28px;'
            f'font-family:Arial,sans-serif;color:#1C1917;font-size:15px;line-height:1.6">{body}'
            f'<p style="font-size:12px;color:#78716C;margin-top:28px">{footer}</p></td></tr></table></td></tr></table>')


def _button(url: str, label: str) -> str:
    return (f'<p style="margin:22px 0"><a href="{escape(url)}" style="background:#B45309;color:#ffffff;'
            f'text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:999px;display:inline-block">{escape(label)}</a></p>')


def _course_lines(course: dict, city: dict, texts: dict) -> str:
    place = texts["online"] if course["online"] else course["address"]
    return (f'<p style="margin:0"><strong>{escape(course["title"])}</strong><br>'
            f'{escape(format_when(course, ZoneInfo(city["timezone"]), texts))}<br>{escape(place)}</p>')


async def _send_confirmation(doc: dict, course: dict, city: dict, texts: dict) -> None:
    confirm = site_url(doc["host"], f'/api/reminders/confirm?token={doc["token"]}')
    cancel = site_url(doc["host"], f'/api/reminders/cancel?token={doc["token"]}')
    body = (f'<p>{escape(texts["reminderConfirmIntro"])}</p>{_course_lines(course, city, texts)}'
            f'{_button(confirm, texts["reminderConfirmButton"])}'
            f'<p style="font-size:13px;color:#57534E">{escape(texts["reminderIgnore"])} '
            f'<a href="{escape(cancel)}" style="color:#92400E">{escape(texts["reminderCancelLink"])}</a></p>')
    await send_email(to=doc["email"], subject=fill(texts["reminderConfirmSubject"], course=course["title"]),
                     html=_layout(texts, city, body), from_name=sender(city, texts), reply_to=city.get("contactEmail"))


async def _send_reminder(doc: dict, course: dict, city: dict, texts: dict) -> None:
    page = site_url(doc["host"], f'/?course={course["id"]}')
    calendar = site_url(doc["host"], f'/api/courses/{course["id"]}/calendar.ics')
    cancel = site_url(doc["host"], f'/api/reminders/cancel?token={doc["token"]}')
    body = (f'<p>{escape(texts["reminderIntro"])}</p>{_course_lines(course, city, texts)}'
            f'{_button(page, texts["reminderViewButton"])}'
            f'<p><a href="{escape(calendar)}" style="color:#92400E">{escape(texts["addToCalendar"])}</a></p>'
            f'<p style="font-size:13px;color:#57534E"><a href="{escape(cancel)}" style="color:#92400E">'
            f'{escape(texts["reminderStopLink"])}</a></p>')
    await send_email(to=doc["email"], subject=fill(texts["reminderSubject"], course=course["title"]),
                     html=_layout(texts, city, body), from_name=sender(city, texts), reply_to=city.get("contactEmail"))


def _wants_json(request: Request) -> bool:
    return "application/json" in request.headers.get("content-type", "") or "application/json" in request.headers.get("accept", "")


@router.post("/reminders")
async def create_reminder(request: Request):
    """JSON from the page script, or a plain form post when JavaScript is off."""
    from server import client_ip, pick_locale  # avoid a circular import at load time
    city = request.state.city
    if city is None:
        raise HTTPException(status_code=404, detail="This site is not configured")
    data = await request.json() if "application/json" in request.headers.get("content-type", "") else dict(await request.form())
    email, course_id = str(data.get("email", "")).strip(), str(data.get("courseId", ""))
    locale = pick_locale(request, city)
    texts = STATE.texts.bundle(locale)

    def reply(status: int, key: str):
        if _wants_json(request):
            return JSONResponse({"message": texts[key]}, status_code=status)
        return RedirectResponse(f"/?course={course_id}", status_code=303)

    course = find_course(await courses_for(locale), course_id)
    if not EMAIL_RE.match(email) or len(email) > 254:
        return reply(400, "reminderBadEmail")
    if course is None or course["start"] <= datetime.now(timezone.utc):
        return reply(404, "courseUnavailableNotice")
    email = email.lower()
    ip = client_ip(request)
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    if (await db.reminders.count_documents({"email": email}) >= MAX_PER_EMAIL
            or await db.reminders.count_documents({"ip": ip, "created_at": {"$gte": hour_ago}}) >= MAX_PER_IP_HOUR):
        return reply(429, "reminderTooMany")
    if await db.reminders.find_one({"email": email, "course_id": course_id}, {"_id": 1}):
        return reply(200, "reminderCheckEmail")
    doc = {"id": str(uuid.uuid4()), "token": secrets.token_urlsafe(24), "email": email, "course_id": course_id,
           "city_id": city["cityId"], "host": request.state.host, "locale": locale, "status": "pending", "ip": ip,
           "created_at": datetime.now(timezone.utc), "start": course["start"], "remind_at": course["start"] - REMIND_BEFORE}
    await db.reminders.insert_one(doc)
    try:
        await _send_confirmation(doc, course, city, texts)
    except EmailUnavailable:
        await db.reminders.delete_one({"id": doc["id"]})
        return reply(503, "reminderEmailDown")
    await record_course_event(city["cityId"], "reminder_signup", course)
    return reply(200, "reminderCheckEmail")


@router.get("/reminders/confirm", response_class=HTMLResponse)
async def confirm_page(request: Request, token: str):
    """Email link scanners follow GET links, so confirming needs a click on this page (a POST)."""
    from server import pick_locale
    city = request.state.city
    texts = STATE.texts.bundle(pick_locale(request, city))
    doc = await db.reminders.find_one({"token": token}, {"_id": 0, "course_id": 1})
    if not doc or city is None:
        return RedirectResponse("/?notice=reminder_invalid", status_code=303)
    course = find_course(await courses_for(pick_locale(request, city)), doc["course_id"])
    title = course["title"] if course else ""
    return HTMLResponse(
        f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{escape(texts["reminderConfirmButton"])}</title></head>'
        f'<body style="font-family:Arial,sans-serif;background:#FAF9F6;color:#1C1917;display:grid;place-items:center;min-height:90vh">'
        f'<form method="post" action="/api/reminders/confirm" style="background:#fff;border:1px solid #E7E5E4;border-radius:16px;padding:32px;max-width:460px">'
        f'<p>{escape(texts["reminderConfirmIntro"])}</p><p><strong>{escape(title)}</strong></p>'
        f'<input type="hidden" name="token" value="{escape(token)}">'
        f'<button type="submit" data-testid="reminder-confirm-button" style="background:#B45309;color:#fff;border:0;border-radius:999px;'
        f'padding:12px 22px;font-weight:bold;font-size:15px;cursor:pointer">{escape(texts["reminderConfirmButton"])}</button></form></body></html>')


@router.post("/reminders/confirm")
async def confirm_reminder(request: Request):
    token = str((await request.form()).get("token", ""))
    doc = await db.reminders.find_one_and_update({"token": token}, {"$set": {"status": "confirmed"}}, projection={"_id": 0})
    if not doc:
        return RedirectResponse("/?notice=reminder_invalid", status_code=303)
    return RedirectResponse(f'/?notice=reminder_confirmed&course={doc["course_id"]}', status_code=303)


@router.get("/reminders/cancel")
async def cancel_reminder(token: str):
    result = await db.reminders.delete_one({"token": token})
    return RedirectResponse("/?notice=" + ("reminder_cancelled" if result.deleted_count else "reminder_invalid"), status_code=303)


async def send_due_reminders() -> int:
    now = datetime.now(timezone.utc)
    await db.reminders.delete_many({"start": {"$lte": now}})  # course started: nothing left to remind
    sent = 0
    async for doc in db.reminders.find({"status": "confirmed", "remind_at": {"$lte": now}}, {"_id": 0}):
        city = STATE.config.cities.get(doc["city_id"])
        texts = STATE.texts.bundle(doc["locale"])
        course = find_course(await courses_for(doc["locale"]), doc["course_id"])
        if city is None or course is None or course["closed"] or course["full"]:
            await db.reminders.delete_one({"id": doc["id"]})
            continue
        try:
            await _send_reminder(doc, course, city, texts)
        except EmailUnavailable:
            continue  # try again on the next run
        await db.reminders.delete_one({"id": doc["id"]})
        sent += 1
    if sent:
        logger.info("Sent %d course reminder(s)", sent)
    return sent


async def _hourly_work() -> None:
    from gifts import retry_failed_gift_emails  # gifts imports this module
    try:
        await send_due_reminders()
    except Exception as exc:
        logger.error("Reminder run failed: %s", exc)
    try:
        await retry_failed_gift_emails()
    except Exception as exc:
        logger.error("Gift email retry failed: %s", exc)


@router.post("/cron/hourly")
async def cron_hourly(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], os.environ["WEBHOOK_CRON_SECRET"]):
        raise HTTPException(status_code=401, detail="Unauthorized")
    run_id = request.headers.get("x-webhook-id") or str(uuid.uuid4())
    try:
        await db.cron_runs.insert_one({"_id": run_id, "at": datetime.now(timezone.utc)})
    except Exception:
        return {"status": "duplicate"}
    background.add_task(_hourly_work)
    return {"status": "accepted"}
