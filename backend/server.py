import asyncio
import json
import logging
import os
import sys
import uuid
from html import escape as html_escape
from zoneinfo import ZoneInfo
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

from fastapi import APIRouter, FastAPI, Request  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from pymongo import ASCENDING, DESCENDING, IndexModel  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from admin_routes import load_admin_state, router as admin_router  # noqa: E402
from clerk_auth import clerk_router  # noqa: E402
from db import client, db  # noqa: E402
from i18n import Texts  # noqa: E402
from calendar_ics import build_ics  # noqa: E402
from course_pages import COURSE_STYLE, format_when, render_courses  # noqa: E402
from courses import TABS, CourseFeed, find_course, load_programs, program_list  # noqa: E402
from home_view import build_view, courses_for, distance_options  # noqa: E402
from insights import is_bot, record_event, router as insights_router  # noqa: E402
from pages import DEFAULT_LOGO, legal_content, render_not_configured, render_page  # noqa: E402
from reminders import router as reminders_router  # noqa: E402
from gifts import router as gifts_router  # noqa: E402
from gift_admin import router as gift_admin_router  # noqa: E402
from roles import move_retired_roles, router as roles_router  # noqa: E402
from site_config import ConfigError, load_config_file, normalize_host, resolve_city, validate_config  # noqa: E402
from state import STATE  # noqa: E402
from storage import init_storage  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("citysites")

TRUST_PROXY = os.environ["TRUST_PROXY"].strip().lower() == "true"
LOG_RETENTION = timedelta(days=90)
UNLOGGED_PREFIXES = ("/api/", "/healthz", "/static/", "/favicon")


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT_DIR / p


# Startup fails here, with every problem listed, when the config is invalid.
try:
    STATE.texts = Texts(_path(os.environ["LOCALES_DIR"]))
    STATE.config_file = _path(os.environ["SITE_CONFIG_FILE"])
    STATE.config = validate_config(load_config_file(STATE.config_file), set(STATE.texts.files))
    programs_raw = json.loads((ROOT_DIR / "config/programs.json").read_text())
    STATE.programs = program_list(programs_raw)
    STATE.feeds = {locale: CourseFeed(os.environ["UNITY_COURSES_API_URL"], load_programs(programs_raw),
                                      int(os.environ["COURSE_CACHE_MINUTES"]) * 60, language=f"{locale}-ca")
                   for locale in ("en", "fr")}
    STATE.places = json.loads((ROOT_DIR / "config/canadian_cities.json").read_text(encoding="utf-8"))
    PLACE_LABELS = [p["label"] for p in STATE.places]
except (ConfigError, ValueError, KeyError) as exc:
    logger.critical("%s", exc)
    raise SystemExit(f"Startup aborted: {exc}")

INDEXES: dict[str, list[IndexModel]] = {
    "access_logs": [
        IndexModel([("ts", ASCENDING)], name="ts_ttl", expireAfterSeconds=int(LOG_RETENTION.total_seconds())),
        IndexModel([("city_id", ASCENDING), ("ts", DESCENDING)], name="city_ts"),
        IndexModel([("host", ASCENDING), ("ts", DESCENDING)], name="host_ts"),
    ],
    "users": [IndexModel([("user_id", ASCENDING)], name="user_id", unique=True)],
    "files": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "insight_events": [
        IndexModel([("ts", ASCENDING)], name="ts_ttl", expireAfterSeconds=int(LOG_RETENTION.total_seconds())),
        IndexModel([("city_id", ASCENDING), ("kind", ASCENDING), ("ts", DESCENDING)], name="city_kind_ts"),
    ],
    "reminders": [
        IndexModel([("token", ASCENDING)], name="token", unique=True),
        IndexModel([("email", ASCENDING), ("course_id", ASCENDING)], name="email_course"),
        IndexModel([("status", ASCENDING), ("remind_at", ASCENDING)], name="due"),
    ],
    "cron_runs": [IndexModel([("at", ASCENDING)], name="at_ttl", expireAfterSeconds=7 * 86400)],
    "gifts": [
        IndexModel([("code", ASCENDING)], name="code", unique=True),
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("gift_giver_id", ASCENDING), ("created_at", DESCENDING)], name="giver"),
        IndexModel([("gift_giver_email", ASCENDING), ("created_at", DESCENDING)], name="giver_email"),
    ],
    "gift_checkouts": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("created_at", ASCENDING)], name="created_ttl", expireAfterSeconds=7 * 86400),
        IndexModel([("ip", ASCENDING), ("created_at", DESCENDING)], name="ip_created"),
    ],
    "gift_payments": [IndexModel([("payment_id", ASCENDING)], name="payment_id", unique=True)],
    "gift_redemptions": [IndexModel([("gift_id", ASCENDING), ("created_at", DESCENDING)], name="gift_created")],
    "gift_failed_lookups": [IndexModel([("at", ASCENDING)], name="at_ttl", expireAfterSeconds=3600)],
    "text_overrides": [IndexModel([("locale", ASCENDING), ("key", ASCENDING)], name="locale_key", unique=True)],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)


app = FastAPI()
api_router = APIRouter(prefix="/api")
_tasks: set = set()


def request_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-host") if TRUST_PROXY else None
    return (forwarded or request.headers.get("host") or "").split(",")[0].strip()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for") if TRUST_PROXY else None
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


async def _insert_visit(doc: dict) -> None:
    try:
        await db.access_logs.insert_one(doc)
    except Exception as exc:
        logger.error("Could not record visit: %s", exc)


def record_visit(request: Request, path: str, status: int) -> None:
    city = request.state.city
    doc = {"id": str(uuid.uuid4()), "ts": datetime.now(timezone.utc), "ip": client_ip(request),
           "host": request.state.host, "path": path[:500], "city_id": city["cityId"] if city else "unknown",
           "status": status, "user_agent": request.headers.get("user-agent", "")[:300]}
    task = asyncio.create_task(_insert_visit(doc))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


@app.middleware("http")
async def city_context(request: Request, call_next):
    host = request_host(request)
    request.state.host = normalize_host(host)
    request.state.city = resolve_city(host, STATE.config)
    response = await call_next(request)
    city_id = request.state.city["cityId"] if request.state.city else "unknown"
    path = request.scope["path"]
    logger.info("cityId=%s host=%s %s %s -> %s", city_id, request.state.host or "-",
                request.method, path, response.status_code)
    if request.method == "GET" and not path.startswith(UNLOGGED_PREFIXES):
        query = request.scope.get("query_string", b"").decode("latin-1")
        full = path + (f"?{query}" if query else "")
        record_visit(request, full, response.status_code)
    return response


def pick_locale(request: Request, city: dict | None) -> str:
    chosen = request.cookies.get("lang")
    if chosen in STATE.config.locales:
        return chosen
    return city["defaultLocale"] if city else "en"


def looks_signed_in(request: Request) -> bool:
    """Clerk keeps a non-zero __client_uat cookie on the site's domain while a user is signed in (display hint only)."""
    return any(name.startswith("__client_uat") and value not in ("", "0") for name, value in request.cookies.items())


def unknown_host_response(request: Request, locale: str):
    logger.warning("Unknown host %r: no city is configured for it", request.state.host)
    if STATE.config.unknown_host == "redirect":
        return RedirectResponse(STATE.config.redirect_url, status_code=302)
    return HTMLResponse(render_not_configured(STATE.texts.bundle(locale), locale), status_code=404)


@app.get("/healthz")
@api_router.get("/healthz")
async def healthz():
    return {"status": "ok"}


def base_url(request: Request) -> str:
    scheme = "http" if request.state.host.startswith(("localhost", "127.0.0.1")) else "https"
    return f"{scheme}://{request.state.host}"


def set_view_cookies(response, view) -> None:
    for name, (value, max_age) in view.cookies.items():
        response.set_cookie(name, value, max_age=max_age, samesite="lax", path="/")


def language_redirect(lang: str, target: str):
    response = RedirectResponse(target, status_code=303)
    if lang in STATE.config.locales:
        response.set_cookie("lang", lang, max_age=365 * 86400, samesite="lax", path="/")
    return response


async def home_view(request: Request, city: dict, locale: str):
    texts = STATE.texts.bundle(locale)
    view = await build_view(city, request.query_params, request.cookies, client_ip(request), locale, texts)
    return view, render_courses(view, distance_options(city), base_url(request), PLACE_LABELS)


def share_meta(view, request: Request) -> str:
    course = view.shared
    if not course:
        return ""
    place = view.texts["online"] if course["online"] else course["city"]
    desc = " · ".join(x for x in (format_when(course, ZoneInfo(view.city["timezone"]), view.texts), place) if x)
    url = f'{base_url(request)}/?course={course["id"]}'
    return "".join(f'<meta property="{k}" content="{html_escape(v)}">' for k, v in
                   (("og:title", course["title"]), ("og:description", desc), ("og:url", url), ("og:type", "website"))) + \
        f'<meta name="description" content="{html_escape(desc)}">'


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, lang: str | None = None):
    city = request.state.city
    if lang is not None:
        tab = request.query_params.get("tab")
        return language_redirect(lang, f"/?tab={tab}" if tab in TABS and tab != TABS[0] else "/")
    locale = pick_locale(request, city)
    if city is None:
        return unknown_host_response(request, locale)
    view, content = await home_view(request, city, locale)
    if not is_bot(request.headers.get("user-agent", "")):
        await record_event(city["cityId"], "tab_view", tab=view.tab)
    page = render_page(city, view.texts, locale, STATE.config.locales, signed_in=looks_signed_in(request), content=content,
                       tab=view.tab, cookie_ok=request.cookies.get("cookie_ok") == "1",
                       title=view.shared["title"] if view.shared else None, head=share_meta(view, request),
                       year=datetime.now(timezone.utc).year)
    response = HTMLResponse(page, headers={"Cache-Control": "no-store"})
    set_view_cookies(response, view)
    return response


@app.get("/privacy", response_class=HTMLResponse)
@app.get("/terms", response_class=HTMLResponse)
async def legal_page(request: Request, lang: str | None = None):
    kind = request.scope["path"].strip("/")
    city = request.state.city
    if lang is not None:
        return language_redirect(lang, f"/{kind}")
    locale = pick_locale(request, city)
    if city is None:
        return unknown_host_response(request, locale)
    texts = STATE.texts.bundle(locale)
    return HTMLResponse(render_page(city, texts, locale, STATE.config.locales, signed_in=looks_signed_in(request),
                                    content=legal_content(kind, city, texts), path=f"/{kind}", title=texts[f"{kind}Title"],
                                    cookie_ok=request.cookies.get("cookie_ok") == "1", year=datetime.now(timezone.utc).year))


@api_router.get("/home-content")
async def home_content(request: Request):
    """Same course content as the server-rendered home, for hosts where / is served by the SPA."""
    city = request.state.city
    if city is None:
        return JSONResponse({"detail": "not_configured"}, status_code=404)
    view, html = await home_view(request, city, pick_locale(request, city))
    if not is_bot(request.headers.get("user-agent", "")):
        await record_event(city["cityId"], "tab_view", tab=view.tab)
    response = JSONResponse({"html": html, "css": COURSE_STYLE})
    set_view_cookies(response, view)
    return response


@api_router.get("/legal/{kind}")
async def legal_api(request: Request, kind: str):
    city = request.state.city
    if city is None or kind not in ("privacy", "terms"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return {"html": legal_content(kind, city, STATE.texts.bundle(pick_locale(request, city))), "css": COURSE_STYLE}


@api_router.get("/courses/{course_id}/calendar.ics")
async def course_calendar(request: Request, course_id: str):
    city = request.state.city
    locale = pick_locale(request, city)
    course = find_course(await courses_for(locale), course_id)
    if city is None or course is None:
        return JSONResponse({"detail": "Course not found"}, status_code=404)
    ics = build_ics(course, f"{base_url(request)}/?course={course_id}", STATE.texts.bundle(locale))
    return Response(ics, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="course-{course_id}.ics"'})


@api_router.get("/site")
async def site(request: Request):
    city = request.state.city
    locale = pick_locale(request, city)
    texts = STATE.texts.bundle(locale)
    public_city = None
    if city:
        public_city = {k: city.get(k) for k in ("cityId", "displayName", "timezone", "contactEmail", "contactPhone", "defaultLocale")}
        public_city["logoUrl"] = city.get("logoUrl") or DEFAULT_LOGO
    else:
        logger.warning("Unknown host %r requested /api/site", request.state.host)
    return {"configured": city is not None, "city": public_city, "locale": locale,
            "locales": list(STATE.config.locales), "texts": texts, "defaultLogo": DEFAULT_LOGO}


class Visit(BaseModel):
    path: str


@api_router.post("/track", status_code=204)
async def track(request: Request, body: Visit):
    if body.path.startswith("/"):
        record_visit(request, body.path, 200)


app.include_router(api_router)
app.include_router(clerk_router)
app.include_router(roles_router)
app.include_router(admin_router)
app.include_router(insights_router)
app.include_router(reminders_router)
app.include_router(gifts_router)
app.include_router(gift_admin_router)
app.mount("/api/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _init_storage_quietly():
    try:
        init_storage()
        logger.info("Object storage initialised")
    except Exception as exc:
        logger.error("Object storage init failed: %s", exc)


@app.on_event("startup")
async def startup():
    app.state.index_task = asyncio.create_task(ensure_indexes())
    await move_retired_roles()
    await load_admin_state()
    logger.info("Site config loaded from %s: %d cities, %d hosts",
                STATE.source, len(STATE.config.cities), len(STATE.config.hosts))
    asyncio.create_task(run_in_threadpool(_init_storage_quietly))



@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.index_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.index_task
    client.close()
