"""Server-rendered course tabs and cards for a city home page."""

import re
from html import escape
from zoneinfo import ZoneInfo

from calendar_ics import google_link
from courses import TABS

COURSE_STYLE = """
.cs-main{max-width:1100px;margin:0 auto;padding:48px 24px 96px}
.cs-title{font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;font-size:clamp(1.9rem,4vw,3rem);letter-spacing:-.02em;margin:0;line-height:1.15;animation:cs-rise .6s ease-out both}
.cs-sub{color:#57534E;margin:10px 0 0;font-size:15px}
.cs-tabs{display:flex;gap:6px;margin:32px 0 24px;border-bottom:1px solid #E7E5E4;overflow-x:auto}
.cs-tabs a{display:flex;align-items:center;gap:8px;white-space:nowrap;padding:12px 16px;color:#57534E;text-decoration:none;font-weight:600;font-size:15px;border-bottom:3px solid transparent;margin-bottom:-1px;transition:color .2s,border-color .2s}
.cs-tabs a:hover{color:#1C1917}
.cs-tabs a[aria-current=page]{color:#92400E;border-bottom-color:#B45309}
.cs-tabs a:focus-visible{outline:3px solid #0284C7;outline-offset:-3px;border-radius:6px}
.cs-count{font-size:12px;background:#F5F5F4;color:#44403C;border-radius:999px;padding:1px 8px}
.cs-tabs a[aria-current=page] .cs-count{background:#FEF3C7;color:#78350F}
.cs-list{list-style:none;margin:0;padding:0;display:grid;gap:12px}
.cs-card{background:#fff;border:1px solid #E7E5E4;border-radius:16px;transition:border-color .2s,box-shadow .2s}
.cs-card:hover{border-color:#FCD34D;box-shadow:0 6px 24px -12px rgba(120,53,15,.25)}
.cs-card summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:64px 1fr auto;gap:18px;align-items:center;padding:16px 20px}
.cs-card summary::-webkit-details-marker{display:none}
.cs-card summary:focus-visible{outline:3px solid #0284C7;outline-offset:2px;border-radius:16px}
.cs-date{display:flex;flex-direction:column;align-items:center;justify-content:center;background:#FFFBEB;border-radius:12px;height:64px;color:#78350F}
.cs-date b{font-family:'Plus Jakarta Sans',sans-serif;font-size:24px;line-height:1}
.cs-date span{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}
.cs-name{font-family:'Plus Jakarta Sans',sans-serif;font-size:17px;font-weight:600;margin:0;color:#1C1917}
.cs-meta{margin:3px 0 0;color:#57534E;font-size:14px}
.cs-badges{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.cs-badge{font-size:12px;font-weight:600;border-radius:999px;padding:2px 10px;background:#F5F5F4;color:#44403C}
.cs-badge.near{background:#ECFDF5;color:#065F46}
.cs-badge.warn{background:#FEF2F2;color:#991B1B}
.cs-chev{width:28px;height:28px;border-radius:999px;border:1px solid #E7E5E4;display:grid;place-items:center;color:#57534E;transition:transform .2s}
.cs-card[open] .cs-chev{transform:rotate(180deg)}
.cs-body{border-top:1px solid #F5F5F4;padding:18px 20px 22px 102px;display:grid;gap:14px}
.cs-body dl{margin:0;display:grid;grid-template-columns:150px 1fr;gap:8px 16px;font-size:14px}
.cs-body dt{color:#78716C;font-weight:600}
.cs-body dd{margin:0;color:#1C1917}
.cs-body ul{margin:0;padding:0;list-style:none}
.cs-body a{color:#92400E}
.cs-register{justify-self:start;background:#B45309;color:#fff!important;text-decoration:none;font-weight:600;font-size:14px;padding:10px 20px;border-radius:999px;transition:background-color .2s}
.cs-register:hover{background:#92400E}
.cs-empty{background:#fff;border:1px dashed #D6D3D1;border-radius:16px;padding:40px;color:#57534E;text-align:center}
.cs-controls{display:flex;flex-wrap:wrap;align-items:flex-end;gap:12px;margin:0 0 20px}
.cs-field input,.cs-field select{height:42px;box-sizing:border-box}
.cs-field{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:#57534E;text-transform:uppercase;letter-spacing:.06em}
.cs-field select,.cs-remind input{font:inherit;font-size:14px;text-transform:none;letter-spacing:0;font-weight:500;color:#1C1917;background:#fff;border:1px solid #D6D3D1;border-radius:10px;padding:9px 12px;min-width:170px}
.cs-field input{font:inherit;font-size:14px;text-transform:none;letter-spacing:0;font-weight:500;color:#1C1917;background:#fff;border:1px solid #D6D3D1;border-radius:10px;padding:9px 12px;min-width:220px}
.cs-apply{font:inherit;font-weight:600;font-size:14px;border:0;color:#fff;background:#B45309;border-radius:999px;padding:10px 22px;cursor:pointer;transition:background-color .2s}
.cs-apply:hover{background:#92400E}
.cs-actions{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.cs-action{font:inherit;font-size:14px;font-weight:600;color:#44403C!important;background:#fff;border:1px solid #D6D3D1;border-radius:999px;padding:9px 16px;text-decoration:none;cursor:pointer;transition:background-color .2s}
.cs-action:hover{background:#F5F5F4}
.cs-status{font-size:13px;color:#065F46;margin:0}.cs-status.cs-error{color:#B91C1C}
.cs-remind{display:grid;gap:6px;border-top:1px dashed #E7E5E4;padding-top:14px;font-size:14px}
.cs-remind label{font-weight:700;color:#44403C}.cs-remind-row{display:flex;flex-wrap:wrap;gap:8px}
.cs-hint{margin:0;font-size:12px;color:#78716C}
.cs-notice{background:#ECFDF5;border:1px solid #A7F3D0;color:#065F46;border-radius:12px;padding:12px 16px;margin:0 0 20px;font-size:14px}
@keyframes cs-rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@media (max-width:640px){.cs-field{width:100%}.cs-field input,.cs-field select{width:100%;min-width:0}.cs-apply{width:100%}.cs-tabs{flex-wrap:wrap;gap:2px}.cs-tabs a{padding:10px 10px;font-size:14px}.cs-card summary{grid-template-columns:52px 1fr;gap:12px;padding:14px}.cs-chev{display:none}
.cs-date{height:52px}.cs-date b{font-size:19px}.cs-body{padding:16px}.cs-body dl{grid-template-columns:1fr;gap:2px}.cs-body dd{margin-bottom:8px}}
@media (prefers-reduced-motion:reduce){.cs-title{animation:none}}
"""

TAB_TEXT = {"newcomer": "tabNewcomer", "advanced": "tabAdvanced", "online": "tabOnline"}
CHEVRON = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
           'aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>')


def fill(template: str, **values) -> str:
    """Fill {name} placeholders; unknown placeholders stay as typed (texts are admin-editable)."""
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def _date(dt, texts) -> str:
    weekday = texts["weekdaysShort"].split(",")[dt.weekday()].strip()
    month = texts["monthsShort"].split(",")[dt.month - 1].strip()
    return fill(texts["dateFormat"], weekday=weekday, month=month, day=dt.day)


def _time(dt, texts) -> str:
    if texts["timeFormat"] == "24h":
        return f"{dt.hour} h {dt.minute:02d}"
    return f"{dt.hour % 12 or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


CLOCK_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)", re.IGNORECASE)


def _schedule_line(line: str, texts) -> str:
    """The API writes schedules in 12h English; switch to 24h when the locale asks for it."""
    if texts["timeFormat"] != "24h":
        return line
    def to24(m):
        hour = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "PM" else 0)
        return f"{hour} h {m.group(2)}"
    return CLOCK_RE.sub(to24, line)


def format_when(course, tz, texts) -> str:
    start, end = course["start"].astimezone(tz), course["end"].astimezone(tz)
    dates = _date(start, texts) if start.date() >= end.date() else f"{_date(start, texts)} – {_date(end, texts)}"
    return f"{dates} · {_time(start, texts)}"


def _money(amount, currency) -> str:
    value = f"{amount:g}" if isinstance(amount, float) else str(amount)
    return f"${value} {currency}".strip()


def _fees(course, texts) -> str:
    fees = course["fees"]
    parts = [_money(fees["fee"], course["currency"])] if fees["fee"] else []
    parts += [f'{texts[k]} {_money(fees[k], course["currency"])}' for k in ("studentFee", "repeaterFee", "seniorFee") if fees[k]]
    return " · ".join(parts)


def _contact(course) -> str:
    parts = [escape(course["contactName"])] if course["contactName"] else []
    if course["contactEmail"]:
        parts.append(f'<a href="mailto:{escape(course["contactEmail"])}">{escape(course["contactEmail"])}</a>')
    parts += [f'<a href="tel:{escape(p)}">{escape(p)}</a>' for p in course["phones"]]
    return " · ".join(parts)


def _actions(course, texts, page_url) -> str:
    cid = escape(course["id"])
    url = course["registerUrl"]
    parts = []
    if course["closed"] or course["full"]:
        parts.append(f'<span class="cs-badge warn">{escape(texts["courseFull" if course["full"] else "registrationClosed"])}</span>')
    elif url.startswith(("https://", "http://")):
        parts.append(f'<a class="cs-register" href="{escape(url)}" target="_blank" rel="noopener noreferrer" '
                     f'data-track="register_click" data-testid="course-register-link-{cid}">{escape(texts["register"])}</a>')
    parts.append(f'<a class="cs-action" href="/api/courses/{cid}/calendar.ics" data-track="calendar_add" '
                 f'data-testid="course-calendar-ics-{cid}">{escape(texts["addToCalendar"])}</a>')
    parts.append(f'<a class="cs-action" href="{escape(google_link(course, page_url, texts))}" target="_blank" '
                 f'rel="noopener noreferrer" data-track="calendar_add" data-testid="course-calendar-google-{cid}">'
                 f'{escape(texts["googleCalendar"])}</a>')
    parts.append(f'<button type="button" class="cs-action" data-share="{escape(page_url)}" data-title="{escape(course["title"])}" '
                 f'data-copied="{escape(texts["linkCopied"])}" data-testid="course-share-button-{cid}">{escape(texts["share"])}</button>'
                 f'<span class="cs-status" role="status" data-testid="course-share-status-{cid}"></span>')
    return f'<div class="cs-actions">{"".join(parts)}</div>'


def _remind_form(course, texts) -> str:
    cid = escape(course["id"])
    return (f'<form class="cs-remind" method="post" action="/api/reminders" data-remind data-testid="course-remind-form-{cid}">'
            f'<input type="hidden" name="courseId" value="{cid}">'
            f'<label for="remind-{cid}">{escape(texts["remindMe"])}</label>'
            f'<div class="cs-remind-row"><input id="remind-{cid}" type="email" name="email" required autocomplete="email" '
            f'placeholder="{escape(texts["emailPlaceholder"])}" data-testid="course-remind-email-{cid}">'
            f'<button type="submit" class="cs-action" data-testid="course-remind-submit-{cid}">{escape(texts["remindButton"])}</button></div>'
            f'<p class="cs-hint">{escape(texts["remindHint"])}</p>'
            f'<p class="cs-status" role="status" data-testid="course-remind-status-{cid}"></p></form>')


def _details(course, texts, page_url) -> str:
    timings = "".join(f"<li>{escape(_schedule_line(t, texts))}</li>" for t in course["timings"])
    rows = [
        ("schedule", timings and f"<ul>{timings}</ul>"),
        ("venue", escape(course["address"]) if not course["online"] else ""),
        ("teachers", escape(", ".join(course["teachers"]))),
        ("fee", escape(_fees(course, texts))),
        ("language", escape(", ".join(course["languages"]))),
        ("contact", _contact(course)),
    ]
    items = "".join(f"<dt>{escape(texts[k])}</dt><dd>{v}</dd>" for k, v in rows if v)
    return f"<dl>{items}</dl>{_actions(course, texts, page_url)}{_remind_form(course, texts)}"


def _badges(row, view) -> str:
    course = row["course"]
    texts = view.texts
    badges = []
    if course["online"]:
        badges.append(f'<span class="cs-badge">{escape(texts["online"])}</span>')
    if view.tab == "online" and row["near"]:
        badges.append(f'<span class="cs-badge near">{escape(fill(texts["nearCity"], city=view.place or view.city["displayName"]))}</span>')
    if row["distanceKm"] is not None and view.tab != "online":
        badges.append(f'<span class="cs-badge">{escape(fill(texts["kmAway"], km=round(row["distanceKm"])))}</span>')
    if course["closed"] or course["full"]:
        badges.append(f'<span class="cs-badge warn">{escape(texts["courseFull" if course["full"] else "registrationClosed"])}</span>')
    return f'<div class="cs-badges">{"".join(badges)}</div>' if badges else ""


def _card(row, view, tz, base_url) -> str:
    course, texts = row["course"], view.texts
    start = course["start"].astimezone(tz)
    month = texts["monthsShort"].split(",")[start.month - 1].strip()
    place = course["city"] if not course["online"] else (course["city"] and f'{texts["online"]} · {course["city"]}')
    meta = " · ".join(x for x in (format_when(course, tz, texts), place) if x)
    cid = escape(course["id"])
    is_open = course["id"] == view.open_id
    page_url = f'{base_url}/?course={course["id"]}'
    return (f'<li id="course-{cid}"><details class="cs-card" data-course="{cid}"{" open data-focus" if is_open else ""} '
            f'data-testid="course-card-{cid}"><summary data-testid="course-card-toggle-{cid}">'
            f'<div class="cs-date" aria-hidden="true"><span>{escape(month)}</span><b>{start.day}</b></div>'
            f'<div><h3 class="cs-name">{escape(course["title"])}</h3><p class="cs-meta">{escape(meta)}</p>'
            f'{_badges(row, view)}</div><span class="cs-chev">{CHEVRON}</span></summary>'
            f'<div class="cs-body" data-testid="course-details-{cid}">{_details(course, texts, page_url)}</div></details></li>')


def _tabs(view) -> str:
    links = "".join(
        f'<a href="/?tab={t}" aria-current="{"page" if t == view.tab else "false"}" data-testid="tab-{t}">'
        f'{escape(view.texts[TAB_TEXT[t]])}<span class="cs-count" data-testid="tab-count-{t}">{view.counts[t]}</span></a>'
        for t in TABS)
    return f'<nav class="cs-tabs" aria-label="{escape(view.texts["coursesLabel"])}" data-testid="course-tabs">{links}</nav>'


def _controls(view, distances, places) -> str:
    texts = view.texts
    km_options = "".join(f'<option value="{km:g}"{" selected" if km == view.km else ""}>{escape(fill(texts["kmOption"], km=f"{km:g}"))}</option>'
                         for km in distances)
    total = sum(n for _, _, n in view.programs)
    program_options = f'<option value="">{escape(fill(texts["allPrograms"], count=total))}</option>' + "".join(
        f'<option value="{escape(slug)}"{" selected" if slug == view.program else ""}>{escape(name)} ({n})</option>'
        for slug, name, n in view.programs)
    place_options = "".join(f'<option value="{escape(p)}"></option>' for p in places)
    return (f'<form class="cs-controls" method="get" action="/" data-testid="course-filters">'
            f'<input type="hidden" name="tab" value="{view.tab}">'
            f'<label class="cs-field">{escape(texts["placeLabel"])}<input name="place" list="cs-places" autocomplete="off" '
            f'value="{escape(view.place or view.city["displayName"])}" data-testid="place-input"></label>'
            f'<datalist id="cs-places">{place_options}</datalist>'
            f'<label class="cs-field">{escape(texts["distanceLabel"])}<select name="km" data-testid="distance-select">{km_options}</select></label>'
            f'<label class="cs-field">{escape(texts["programLabel"])}<select name="program" data-testid="program-filter-select">{program_options}</select></label>'
            f'<button type="submit" class="cs-apply" data-testid="apply-filters-button">{escape(texts["apply"])}</button></form>')


def _notices(view) -> str:
    texts = view.texts
    items = []
    if view.notice:
        items.append((view.notice, texts[{"reminder_confirmed": "reminderConfirmedNotice", "reminder_cancelled": "reminderCancelledNotice",
                                           "reminder_invalid": "reminderInvalidNotice"}[view.notice]]))
    if view.course_missing:
        items.append(("course_missing", texts["courseUnavailableNotice"]))
    if view.place_failed:
        items.append(("place_not_found", fill(texts["placeNotFound"], place=view.place_failed, city=view.city["displayName"])))
    return "".join(f'<p class="cs-notice" role="status" data-testid="notice-{k}">{escape(v)}</p>' for k, v in items)


def render_courses(view, distances, base_url, places=()) -> str:
    """Main content: heading, controls, tabs and the selected tab's courses."""
    city, texts, tab = view.city, view.texts, view.tab
    place = view.place or city["displayName"]
    values = {"city": place, "radius": f"{view.km:g}", "months": city["monthsAhead"]}
    heading = fill(texts["coursesNearHeading" if view.place else "coursesHeading"], **values)
    sub = fill(texts["onlineSub" if tab == "online" else "nearbySub"], **values)
    has_location = city.get("latitude") is not None and city.get("longitude") is not None
    if view.failed:
        listing = f'<p class="cs-empty" role="status" data-testid="courses-unavailable">{escape(texts["coursesUnavailable"])}</p>'
    elif not has_location and not view.place and tab != "online":
        listing = f'<p class="cs-empty" role="status" data-testid="courses-location-missing">{escape(texts["locationMissing"])}</p>'
    elif not view.rows:
        listing = f'<p class="cs-empty" role="status" data-testid="courses-empty">{escape(texts["noCourses"])}</p>'
    else:
        tz = ZoneInfo(city["timezone"])
        listing = f'<ul class="cs-list" data-testid="course-list">{"".join(_card(r, view, tz, base_url) for r in view.rows)}</ul>'
    return (f'<main class="cs-main" data-testid="courses-page">{_notices(view)}'
            f'<h1 class="cs-title" data-testid="courses-heading">{escape(heading)}</h1>'
            f'<p class="cs-sub" data-testid="courses-subheading">{escape(sub)}</p>'
            f'{_tabs(view)}{_controls(view, distances, places)}<section aria-live="polite" data-testid="tab-panel-{tab}">{listing}</section></main>')
