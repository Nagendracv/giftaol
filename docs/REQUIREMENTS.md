# Requirements: Multi-City Art of Living Course Sites

**Status:** As built (rebuild specification) · **Version:** 4.0 · **Date:** 2026-11-15
**Purpose:** Everything needed to rebuild this app with the same behaviour. It combines the original requirements (rev. 2), rev. 3 and every decision made during the build.

---

## 0. Summary

One web application serves many city websites. The web address (host) that a visitor uses decides which city's site they see, for example `aolottawa.ca` → Ottawa. Each site lists Art of Living courses near its city, taken live from the Art of Living **Unity courses API**. Courses appear in three tabs: Newcomer, Advanced and Online.

Visitors can:
- choose another city, a distance and a program
- open course details inline
- add a course to their calendar or share it
- ask for an email reminder

Signed-in admins manage the city configuration, logos, English/French texts and users, and review visit logs and visit insights.

Adding a city takes **configuration only**, with no code changes.

---

## 1. Glossary

| Term | Meaning |
|---|---|
| City (tenant) | A location the platform serves. It has a stable `cityId` slug (`ottawa`). |
| Host | The HTTP `Host` value, lower-cased, with any non-default port (`localhost:5623`, `aolottawa.ca`). |
| Site config | The JSON file (or the admin-saved copy) that maps hosts to cities and holds per-city settings. |
| Course | A scheduled Art of Living offering from the Unity API. |
| Place | A Canadian city or town that a visitor can pick to centre the course search. |
| Tab | Newcomer, Advanced or Online. |

---

## 2. Architecture (reference build)

| Part | Choice used | Notes |
|---|---|---|
| Backend | Python FastAPI | Renders the public pages as server-side HTML and serves the JSON API under `/api`. |
| Frontend | React SPA (CRA + Tailwind + shadcn) | Used for sign-in, sign-up, the dashboard and admin. It also falls back to rendering `/`, `/privacy` and `/terms` when those paths are not routed to the backend. |
| Database | MongoDB | Admin config override, text overrides, access logs, insight events, users, reminders, file records, cron run ids. |
| Auth | Emergent-managed Clerk | Email/password and Google sign-in, using Clerk's prebuilt sign-in/sign-up components. |
| File storage | Emergent Object Storage | Uploaded city logos. |
| Email | Emergent-managed Resend | Reminder and confirmation emails. |
| Scheduler | Emergent platform cron (`.emergent/crons.yml`) | Runs hourly. |
| Source control | Local git | Small commits, no remote. |

**Routing in the dev and preview environment:** a dev-server proxy (`frontend/src/setupProxy.js`) sends `/`, `/healthz`, `/privacy`, `/terms` and `/api/*` to the backend and keeps the original `Host` header. All other paths go to the SPA. The SPA calls a **relative** `/api` (same origin) so the backend sees the visitor's host.

**Hosting limit found (Emergent):** each published app supports one custom domain. Serving several city domains from one deployment needs hosting where you control the domains, such as your own server or your own Cloudflare zone. A hosts-file trick against the shared preview edge fails with Cloudflare error 1001.

---

## 3. Host → city resolution

- **R-1** At startup, the app loads a JSON site config chosen by the `SITE_CONFIG_FILE` env var. The files are `backend/config/sites.json` (production) and `backend/config/sites.local.json` (local/preview).
- **R-2** Host normalisation is a **pure function** `normalize_host(raw)`:
  - Take the first value if comma-separated, trim it and lower-case it.
  - Drop a trailing dot.
  - Strip ports 80 and 443. Keep any other port, so `localhost:5623` ≠ `localhost:5624`.
  - Support IPv6 literals such as `[::1]:8080`.
- **R-3** `resolve_city(host, config)` is a pure O(1) dictionary lookup with no database call. `www.` only matches when it is listed, and there are no wildcards.
- **R-4** When `TRUST_PROXY=true`, use `X-Forwarded-Host` (and the first `X-Forwarded-For` value for the client IP). Otherwise use `Host` and the socket address.
- **R-5** City resolution happens once per request in middleware, which stores `request.state.city` and `request.state.host`.
- **R-6** Every request log line includes `cityId=<id|unknown> host=<host> METHOD path -> status`.
- **R-7 Unknown host:** respond with HTTP 404 and a neutral page ("This site is not configured"), and log a WARNING. If `defaultBehavior.unknownHost` is `"redirect"`, respond with a 302 to `redirectUrl` instead.
- **R-8** `/healthz` and `/api/healthz` return 200 `{"status":"ok"}` for any host.

### 3.1 Site config schema

```json
{
  "locales": ["en", "fr"],
  "defaultBehavior": { "unknownHost": "not_found" },
  "cities": [
    {
      "cityId": "ottawa",
      "displayName": "Ottawa",
      "timezone": "America/Toronto",
      "hosts": ["aolottawa.ca", "www.aolottawa.ca", "localhost:5623"],
      "nearbyCityIds": ["gatineau"],
      "defaultLocale": "en",
      "latitude": 45.4215, "longitude": -75.6972,
      "radiusKm": 50, "monthsAhead": 2,
      "contactEmail": "optional", "contactPhone": "optional",
      "logoUrl": "optional", "theme": { "siteTitle": "optional" }
    }
  ]
}
```

Shipped cities:

| City | Latitude, longitude | Radius | Hosts | Notes |
|---|---|---|---|---|
| Ottawa | 45.4215, -75.6972 | 50 km | `aolottawa.ca`, `www.aolottawa.ca`, `localhost:5623`, the preview host | Nearby: gatineau |
| Mississauga | 43.589, -79.6441 | 50 km | `aolmissi.ca`, `localhost:5624` | |
| Gatineau | 45.4765, -75.7013 | 50 km | none | No site of its own |
| Kitchener | 43.4516, -80.4925 | 60 km | `localhost:5625` locally | Covers Cambridge and Waterloo |

All four use 2 months ahead.

### 3.2 Validation (startup and every admin save)
Startup **fails** with a single message listing every problem when any of these is wrong:
- `cityId` is missing, isn't a lowercase slug, or is duplicated.
- `displayName` is empty.
- `timezone` isn't a valid IANA name.
- `hosts` isn't a list of strings.
- The same host appears twice, or under two cities. The message names both cities.
- `nearbyCityIds` references an unknown city or the city itself.
- `defaultLocale` isn't in `locales`, or a locale has no resource file.
- Only one of `latitude`/`longitude` is set, or either is out of range.
- `radiusKm` isn't between 1 and 2000.
- `monthsAhead` isn't an integer from 1 to 12.
- The optional string fields aren't strings, or `theme` isn't an object.
- `defaultBehavior` isn't an object, or `unknownHost` isn't `not_found` or `redirect`.
- `redirectUrl` isn't an http(s) URL when `unknownHost` is `redirect`.

Defaults: `radiusKm` 50, `monthsAhead` 2, `defaultLocale` "en", `nearbyCityIds` [].

### 3.3 Config source of truth
- The file is used until an admin saves the configuration in the app. From then on, the database copy (`site_config` with `_id:"current"`) is used and is validated the same way.
- **Reset to file** deletes the database copy and reloads the file.
- If the saved copy becomes invalid, log an error and fall back to the file.

---

## 4. Text resources and languages

- **T-1** All user-facing public text comes from `backend/locales/<code>.json`, a flat map of key → string. English (`en`) and French (`fr`) are shipped. Adding a language means adding a file and listing it in `locales`.
- **T-2** Files are re-read when they change on disk, so no restart is needed.
- **T-3** Admin edits are stored as overrides (`text_overrides`: locale, key, value) and layered on top. Lookup order: en file → en override → locale file → locale override. Saving an empty value, or one equal to the file text, removes the override.
- **T-4** Placeholders use `{name}` and are filled by safe string replacement, so unknown placeholders stay as typed.
- **T-5** The language is chosen from the `lang` cookie if it is valid, otherwise the city's `defaultLocale`. The switcher links to `<path>?lang=xx&tab=…`, which sets the cookie (12 months) and redirects with a 303.
- **T-6** Date and time formatting comes from the texts: `monthsShort`, `weekdaysShort` (comma lists), `dateFormat` (`{weekday}, {month} {day}` in English, `{weekday} {day} {month}` in French) and `timeFormat` (`12h` in English, `24h` "18 h 00" in French). Schedule lines from the API are converted to 24h for French.
- **T-7** Key list: `logoAlt, languageLabel, signInButton, notConfiguredTitle, notConfiguredMessage, dashboardTitle, dashboardMessage, dashboardLink, adminMenu, backHome, notAllowed, coursesLabel, tabNewcomer, tabAdvanced, tabOnline, coursesHeading, coursesNearHeading, nearbySub, onlineSub, noCourses, coursesUnavailable, locationMissing, kmAway, nearCity, online, schedule, venue, teachers, fee, studentFee, repeaterFee, seniorFee, language, contact, register, registrationClosed, courseFull, monthsShort, weekdaysShort, dateFormat, timeFormat, siteName, footerNav, privacyTitle, termsTitle, cookieLabel, cookieOk, cookieText, distanceLabel, kmOption, programLabel, allPrograms, apply, placeLabel, placeNotFound, placesCredit, addToCalendar, googleCalendar, calendarDetails, share, linkCopied, remindMe, emailPlaceholder, remindButton, remindHint, reminderCheckEmail, reminderBadEmail, reminderTooMany, reminderEmailDown, reminderConfirmedNotice, reminderCancelledNotice, reminderInvalidNotice, courseUnavailableNotice, reminderConfirmSubject, reminderConfirmIntro, reminderConfirmButton, reminderIgnore, reminderCancelLink, reminderSubject, reminderIntro, reminderViewButton, reminderStopLink, emailFooter, legalContactFallback, privacyBody, termsBody`.
- **T-8** Admin screen labels are English only.

---

## 5. Course data source: Unity API

### 5.1 Endpoint
```
GET https://unity.artofliving.org/csapi/courses
    ?type=country&limit=100&distance=0&country=ca&order_by=start_date
    &language=en-ca            (or fr-ca)
    &offset=<page number, starting at 1>
    &mctypes=<comma list>&mctype=<same list>
```
- The base URL, without `language`, is stored in the env var `UNITY_COURSES_API_URL`. The app adds `language`, `offset`, `mctypes` and `mctype`.
- Send a `User-Agent` header.
- One combined request covers **every program type** listed in §5.3, for all of Canada. Pages are fetched until a page has fewer than 100 courses, the `total` is reached, or the last course starts after the furthest window any city needs plus one day. This is typically about 3 pages.
- A radius search by latitude/longitude is **not** supported by the API, so distance filtering is done by the app.

### 5.2 Fields used (per course)

| API field | Use |
|---|---|
| `id` | Course id, used for links, matching across languages and calendar UIDs. |
| `mctype` | Mapped to a program and tab category (§5.3). Unlisted types are dropped. |
| `title` | Shown title. French titles come from the `fr-ca` feed, matched by `id`, falling back to the English title. |
| `start_date`, `end_date` | `YYYY-MM-DD HH:MM:SS` in **UTC**. |
| `bx_course_timings[]` | `{start_time, end_time}` Unix epochs, one per session, used for calendar entries. |
| `course_complex_timing` | Schedule text lines separated by `<br/>`, in the course's local time. Strip tags. |
| `coordinates` | `[longitude, latitude]`. Online courses carry the organiser's location. |
| `is_online_event` | 1 means an online course. |
| `address_short` or `address`, `city` | Venue, and the area label shown on cards. |
| `teachers[]`, `course_language[]` | Shown in the course details. |
| `course_fee`, `student_fee`, `repeater_fee`, `senior_fee`, `currency` | Fees; only values above 0 are shown. |
| `register_url` | External registration link. |
| `is_registration_closed`, `is_event_capacity_full` | Status badges; no Register link when set. |
| `contact_name`, `email`, `phones[]` | Contact details. |

### 5.3 Programs (`backend/config/programs.json`)

| Tab category | slug | Name (FR) | mctypes |
|---|---|---|---|
| newcomer | part-1 | Art of Living Part 1 (Art de vivre - Partie 1) | 1, 58, 517, 736, 737, 759, 1301 |
| newcomer | sahaj | Sahaj Samadhi Meditation | 3, 1303 |
| newcomer | art-excel | ART Excel | 4 |
| newcomer | yes | YES! | 9 |
| newcomer | sri-sri-yoga | Sri Sri Yoga Program | 15, 5009, 1315 |
| newcomer | sky-retreat | SKY Happiness Retreat | 5038, 1669, 1670 |
| newcomer | deep-sleep | Deep Sleep & Anxiety Relief | 5102 |
| newcomer | ip-junior | IP Junior Program | 5103 |
| newcomer | ip-kids | IP Kids Program | 5104 |
| newcomer | ip-teens | IP Teens Program | 5105 |
| advanced | part-2 | Art of Living Part 2 (Art de vivre - Partie 2) | 2, 802, 1302, 1502 |
| advanced | dsn | DSN | 14 |
| advanced | vtp | VTP | 537 |
| advanced | deep-dive | Deep Dive Retreat | 542, 1342 |
| advanced | shakti-kriya | Shakti Kriya | 544 |
| advanced | sanyam | Sanyam | 5023 |

### 5.4 Caching (shared API, avoid load)
- **C-1** Fetch **on first use**, keep the result in memory for `COURSE_CACHE_MINUTES` (60), and allow only one fetch at a time.
- **C-2** English and French are fetched and cached separately. French is fetched only when a French visitor needs it.
- **C-3** If a fetch fails, keep serving the last data. If there is no data yet, show "Courses could not be loaded right now", and don't retry for 2 minutes.
- **C-4** City, distance, program and language changes never trigger extra API calls; all filtering runs on the cached data.

---

## 6. Public home page (`/`, server-rendered)

### 6.1 Header (every page)
- Top left: the logo, which is the city's `logoUrl` if set, otherwise the default Art of Living logo at `/api/static/aol-logo.png`. Next to it is the site name, **"Art of Living <City>"** (French "Art de vivre <City>"), or `theme.siteTitle` if set. The same name is used as the page `<title>`.
- Top right:
  - The EN/FR switcher.
  - **"Sign up / Log in"**, or **"My dashboard"** if the visitor is signed in. The server can't see the session itself, so it uses a non-zero `__client_uat*` cookie from Clerk as the signal.

### 6.2 Heading
- Default heading: "Courses in and around {city}". With a chosen place: "Courses near {place}".
- Subheading for Newcomer/Advanced: "In-person courses within {radius} km, starting in the next {months} months."
- Subheading for Online: "…Organisers near {city} are listed first."

### 6.3 Tabs
- **Newcomer** (the default), **Advanced** and **Online**, as links `/?tab=newcomer|advanced|online`. Each shows a count, and the current tab is marked with `aria-current="page"`.
- Newcomer/Advanced: **in-person** courses of that category within the radius of the centre, starting between now and now + `monthsAhead` calendar months, sorted by start date.
- Online: online courses of **both** categories in the same months. Those whose organiser is within the radius come first (by date, labelled "Organiser near …"), then the rest by date.
- Distance is the great-circle (haversine) distance from the centre, shown as "N km away".

### 6.4 Controls form (GET, submitted with an **Apply** button)
- **City:** an editable text box with a datalist of about 515 Canadian cities and towns over 15,000 people, labelled "Name, PROV". The source is GeoNames `cities15000` filtered to CA, stored in `config/canadian_cities.json` (label, name, latitude, longitude, population), with the most populous first.
  - It starts with the site's own city.
  - Matching ignores case, accents and commas, so "montreal" → "Montréal, QC" and "kitchener on" works. A bare name picks the most populous match.
  - Choosing the site's own city, by name or from the list (e.g. "Ottawa, ON" on the Ottawa site), uses the site's configured centre.
  - Unknown text shows the notice "We couldn't find “X”, so we're showing courses near {city}".
  - The choice is remembered in the `place` cookie for 12 months.
  - **No IP geolocation is used.**
- **Distance:** 10, 25, 50, 100 or 200 km, plus the city's `radiusKm` if it isn't in the list. It starts at `radiusKm` and is remembered in the `km` cookie for 12 months. Invalid values fall back.
- **Program:** "All programs (n)" plus each program that has courses in the current tab, with counts, using the French name where one exists. It sets `?program=<slug>`. Tab links reset it, and an unknown value falls back to All.
- Empty selects are left out of the submitted address.

### 6.5 Course cards (`<details>`, expand inline)
- **Summary:** a date block (month and day), the title, "date range · start time · area" in the **city's time zone**, and badges (Online, km away, organiser near, Registration closed, Course full).
- **Details:**
  - Schedule lines.
  - Venue (in-person only), teachers, fees, language and contact (mailto/tel links).
  - **Register**, which opens in a new tab and is hidden when the course is closed or full.
  - **Add to my calendar** (`.ics`) and **Google Calendar**.
  - **Share**: the phone share sheet, or copy the link with a "Link copied" confirmation.
  - The **Remind me a day before** email form.

### 6.6 Shared course links
- `/?course=<id>` opens the course's tab with that card expanded and scrolled into view. The page includes `og:title`, `og:description` (date · place) and `og:url` meta tags.
- If the visitor's chosen place doesn't contain the course, the site's own area is used instead.
- If the course isn't listed in the site's area, show "This course is no longer available".

### 6.7 Footer (every page)
- Privacy and Terms links, the city's contact email and phone if set, "© <year> <site name>", and "City list from GeoNames" (an attribution required by CC-BY).

### 6.8 Cookie notice
- First-time visitors see a bottom bar saying only essential cookies are used (language, city, distance, sign-in), with a Privacy link and an **OK** button. OK sets `cookie_ok=1` for 12 months. The bar doesn't block the page and works with a keyboard.

### 6.9 Progressive enhancement (`/api/static/site.js`, event delegation)
- Share, cookie OK, the reminder form via `fetch`, scrolling to a shared course, and insight beacons. The page also works without JavaScript: forms post normally.

### 6.10 Privacy and Terms (`/privacy`, `/terms`)
- Server-rendered with the header and footer, in EN/FR, from `privacyBody` / `termsBody`. Paragraphs are separated by blank lines, and lines starting with `## ` are headings. Placeholders: `{site}`, `{city}`, `{contact}`.
- **Privacy** covers visit logs (IP, page, browser, 90 days), accounts, reminder emails (kept until sent, cancelled or the course starts), the city choice cookie, cookies, external registration and contact.
- **Terms** covers use of the site, accuracy of course information, external registration and payment, no warranty and limitation of liability, changes, and contact.
- These are starter texts and need a legal review before going live.

---

## 7. Reminder emails (double opt-in)

1. `POST /api/reminders` accepts JSON or a form with `{courseId, email}`.
2. **Validation:**
   - The email must be valid (400 if not).
   - The course must be in the cache and in the future (404 if not).
   - Each address can have at most 5 reminders, and each IP at most 10 requests per hour (429 above that).
   - A duplicate address + course returns OK without creating another reminder.
3. The app stores `{id, token, email (lower-case), course_id, city_id, host, locale, status:"pending", ip, created_at, start, remind_at = start − 24 h}` and sends a **confirmation email**. The email has a button linking to `https://<host>/api/reminders/confirm?token=…` and a cancel link. If sending fails, the record is deleted and a 503 is returned.
4. `GET /api/reminders/confirm?token` shows a page with a **"Confirm my reminder"** button that POSTs the token. A POST is needed because email link scanners open links automatically. The POST sets `status:"confirmed"` and redirects to `/?notice=reminder_confirmed&course=<id>`.
5. `GET /api/reminders/cancel?token` deletes the reminder and redirects to `/?notice=reminder_cancelled`. Invalid tokens go to `reminder_invalid`.
6. **Hourly cron** `POST /api/cron/hourly` requires `Authorization: Bearer <WEBHOOK_CRON_SECRET>` (401 otherwise). It deduplicates by `X-Webhook-Id`, replies "accepted" at once and works in the background:
   - Delete reminders whose course has started.
   - For confirmed reminders that are due: if the course is gone, closed or full, delete without sending. Otherwise send the reminder (title, date and time in the city's time zone, venue or Online, a link to the course page, an add-to-calendar link, a cancel link) and then delete it.
   - If sending fails, keep the reminder for the next run.
7. Emails go out in the visitor's language. The sender name is `EMAIL_FROM_NAME + " " + city` ("Art of Living Ottawa"), the reply-to is the city's `contactEmail`, and all links are https links to the site's own host. The guardrail gate allows no forms or credential requests in emails, https only, and no shorteners or link-text spoofing.

Cron file `.emergent/crons.yml`:
```yaml
crons:
  - name: hourly-reminders
    cron: "0 * * * *"
    endpoint: "{{BASE_URL}}/api/cron/hourly"
    method: POST
    enabled: true
```

---

## 8. Calendar

- `GET /api/courses/<id>/calendar.ics` returns `text/calendar` as an attachment. It is an RFC 5545 VCALENDAR with **one VEVENT per session** (`UID <id>-<n>@aol-city-sites`), UTC times, SUMMARY (title in the visitor's language), LOCATION (address or "Online"), DESCRIPTION (course page link, register link, contact) and URL. Text is escaped and lines are folded at 75 bytes.
- The Google link is `https://calendar.google.com/calendar/render?action=TEMPLATE&text&dates=<first session>&details=<description + all schedule lines>&location`.

---

## 9. Accounts, roles and the dashboard

- Sign-in uses Clerk's prebuilt components at `/sign-in` and `/sign-up`, with email/password and Google. After sign-in or sign-up the user lands on `/dashboard`, and after sign-out on `/`. One account works on every city site, but each domain has its own sign-in session.
- The backend verifies Clerk session JWTs from `Authorization: Bearer` or the `__session` cookie.
- **Roles:** `admin` and `member` (the default). A `users` record stores user_id, role, email (fetched once from Clerk), env and created_at. `ADMIN_EMAIL` (`nagendracv@gmail.com`) becomes admin on first sign-in **with a verified email**. There must always be at least one admin: demoting the last one returns 409.
- **Dashboard:** shows the city name, "Coming up" and a short message. Admins also see an admin menu: Access logs, Visit insights, Site configuration, Text & languages, Users & admins.

---

## 10. Admin screens (admin role only; 401 without a session, 403 for members)

1. **Access logs:** every page visit, including unknown hosts and SPA routes reported through `POST /api/track`. Health checks and assets are not logged. Columns: time, IP, host, path, city or unknown, status. Filters: city (or unknown) and "host contains". 25 rows per page. Kept **90 days** (TTL index).
2. **Visit insights:** filters by city (or all) and the last 7, 30 or 90 days.
   - **Tab views:** counted server-side on each home render, all three tabs shown, zeros included, bots excluded by user agent.
   - **Most visited courses** (top 50): opened, register clicks, calendar adds, shares and reminder signups.
   - Events come from `POST /api/insights/event` (a sendBeacon with `{kind, courseId}`). Unknown kinds and courses outside the site's area are ignored, and each IP can send at most 30 per minute. Events are stored in `insight_events` with a 90-day TTL.
3. **Site configuration:**
   - Fields per city: cityId, display name, time zone (with suggestions), default language, contact email and phone, hosts (one per line), nearby cities, and the **course search area** (latitude, longitude, radius km, months ahead).
   - Add and remove cities.
   - **Save** validates exactly like startup and shows every error, then applies immediately with no restart.
   - **Reset to file**, and a badge showing whether the configuration comes from the file or was saved by admins.
   - **Logo upload:** PNG, JPEG, WebP, SVG or GIF, up to 2 MB, stored in object storage and served at `/api/logo/<fileId>` with caching. Upload saves immediately, and "Use default logo" clears it.
4. **Text & languages:** every key with English and French side by side. Shows which texts are edited and what the file says. Save applies immediately, and emptying a box reverts it to the file text.
5. **Users & admins:** the list of users who have signed in (email, joined date, role), with a role dropdown. The last admin can't be removed.

---

## 11. API summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/`, `/privacy`, `/terms` | Server-rendered pages. `?lang` sets the language; home also takes `tab`, `place`, `km`, `program`, `course`, `notice`. |
| GET | `/healthz`, `/api/healthz` | Health check. |
| GET | `/api/site` | City info, locale and texts for the SPA. |
| GET | `/api/home-content`, `/api/legal/{kind}` | HTML fragments for the SPA fallback. |
| POST | `/api/track` | SPA page visit. |
| GET | `/api/courses/{id}/calendar.ics` | Calendar file. |
| POST | `/api/reminders` | Ask for a reminder. |
| GET/POST | `/api/reminders/confirm` | Confirm page, then confirm. |
| GET | `/api/reminders/cancel` | Cancel a reminder. |
| POST | `/api/cron/hourly` | Scheduled reminders job. |
| POST | `/api/insights/event` | Course interaction beacon. |
| GET | `/api/logo/{fileId}`, `/api/static/*` | Logos and static files. |
| GET | `/api/clerk/config`, `/api/__clerk/*` | Clerk config and production relay. |
| GET | `/api/me`, `/api/users` | Current user; user list. |
| PATCH | `/api/users/{id}/role` | Change a role. |
| GET/PUT/DELETE | `/api/admin/config` | Read, save, or reset the site config. |
| GET | `/api/admin/timezones` | Time zone list. |
| POST | `/api/admin/cities/{id}/logo` | Upload a logo. |
| GET | `/api/admin/logs`, `/api/admin/insights` | Access logs; visit insights. |
| GET/PUT | `/api/admin/texts` | Read and save texts. |

---

## 12. Cookies

| Cookie | Lifetime | Purpose |
|---|---|---|
| `lang` | 12 months | Language choice. |
| `km` | 12 months | Distance choice. |
| `place` | 12 months | Chosen city. |
| `cookie_ok` | 12 months | Cookie notice dismissed. |
| Clerk `__session`, `__client_uat*` | Set by Clerk | Sign-in. |

There are no advertising or tracking cookies.

---

## 13. Environment variables (backend)

`MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `TRUST_PROXY` (true behind a proxy), `SITE_CONFIG_FILE`, `LOCALES_DIR`, `UNITY_COURSES_API_URL`, `COURSE_CACHE_MINUTES` (60), `ADMIN_EMAIL`, `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `EMERGENT_LLM_KEY` (object storage), `STORAGE_APP_NAME`, `EMERGENT_EMAIL_KEY`, `EMAIL_FROM_NAME` ("Art of Living"), `WEBHOOK_CRON_SECRET`.

Frontend: `REACT_APP_BACKEND_URL`, which is only used to fetch the Clerk config. All other calls use a relative `/api`.

---

## 14. Non-functional requirements

- **Isolation:** no response for one city's host leaks another city's configuration. Course lists depend only on the chosen centre and radius.
- **Performance:** host lookup is in memory. Course data uses the shared hourly cache, about 3 API calls per language per hour at most.
- **Observability:** every log line carries `cityId`. Unknown hosts are logged at WARNING. Fetch and email failures are logged at ERROR.
- **Accessibility (WCAG 2.1 AA aim):** semantic landmarks, `aria-current` on tabs, labelled form fields, visible focus rings, contrast of 4.5:1 or better, reduced-motion support, and keyboard-usable `<details>` cards and the cookie notice.
- **Design:** calm and minimal, with a warm white background (#FAF9F6), an amber primary colour (#B45309), and the DM Sans and Plus Jakarta Sans fonts. On phones, controls and tabs stack.
- **Security:**
  - HTTPS in production.
  - Forwarded headers are trusted only when configured.
  - Admin APIs are role-checked.
  - The cron endpoint is protected by a bearer secret.
  - Reminders need a confirmation POST and are rate-limited.
  - Server pages escape every value.
- **Privacy:** no IP geolocation. Reminder emails are deleted after use. Logs and insights expire after 90 days.

---

## 15. Acceptance criteria (each has an automated test where possible)

1. A request with `Host: localhost:5623` returns 200 with "Courses in and around Ottawa". `localhost:5624` returns "…Mississauga" with config changes only.
2. `Host: unknown.example` → 404 "This site is not configured", plus a warning log.
3. `AOLOTTAWA.CA`, `aolottawa.ca:443` and `aolottawa.ca.` all resolve to Ottawa. `localhost:5625` ≠ `localhost:5623`. `www.` matches only when listed.
4. Startup fails, listing the problems, for a duplicate host, a duplicate cityId, an unknown nearby city, a bad time zone, or a bad area value.
5. `/healthz` returns 200 for any host, and log lines include `cityId=`.
6. Changing a value in `en.json` changes the page without code changes. An admin override takes effect immediately, and clearing it reverts to the file.
7. Newcomer shows only in-person newcomer types within the radius and window. Advanced shows only advanced types. Online shows near organisers first.
8. Unlisted program types, already-started courses and courses beyond `monthsAhead` never appear.
9. Times display in the city's time zone (e.g. 23:00 UTC → "6:00 PM" in Toronto). French uses French dates and 24-hour times.
10. Distance 200 → `?km=200`, which is remembered after a reload. `km=abc` → the default.
11. City "Kitchener, ON" + Apply → "Courses near Kitchener, ON", remembered. "Atlantis" → notice and Ottawa courses. "Ottawa, ON" on the Ottawa site → "Courses in and around Ottawa".
12. Program "sahaj" shows only Sahaj courses. An unknown program shows all.
13. `/?course=<id>` opens the right tab with the card expanded and og tags present. An unknown id shows "no longer available".
14. The `.ics` file has one VEVENT per session with correct UTC times. The Google link goes to calendar.google.com.
15. A reminder request → confirmation email. GET confirm shows a button, and POST confirms. The cron (with the secret) sends due reminders and deletes them. A wrong secret → 401. Invalid email → 400.
16. The header shows "Art of Living Ottawa". The footer has Privacy, Terms and the GeoNames credit. The cookie notice is hidden after OK.
17. In French, Part 1 titles read "Art de vivre - Partie 1".
18. Admin pages: members get 403. The site config validation errors show. Logo upload appears on the site. The last admin can't be demoted (409). Insights show tab views and courses after card opens.

---

## 16. Non-goals (as built)

- Payments or in-app registration; registration links out to the existing system.
- IP or GPS geolocation, and postal-code search.
- Visitors changing the months window.
- Cookie preference settings, which aren't needed with essential cookies only.
- Wildcard subdomains per city.
- Separate codebases or deployments per city.
- A course admin UI: courses come only from the Unity API.

## 17. Decision log

| Decision | Choice |
|---|---|
| Unknown host | 404, with a redirect option in config. |
| Languages | EN + FR, from resource files with admin overrides. |
| Course source | Unity API, one Canada-wide request, lazy hourly cache. |
| Online courses | Own tab; organisers within the radius first. |
| Course click | Expand inline (details + Register); a shareable link per course. |
| Location | IP-based "Near me" was tried and **removed**, because the visitor's provider placed them in Toronto. Replaced by an editable Canadian city picker with an Apply button, defaulting to the site's city. |
| City list | GeoNames cities over 15,000 people (≈515), CC-BY credited. |
| Reminders | Double opt-in, about 24 h before the start, deleted after use, hourly cron. |
| Kitchener demo city | 60 km radius to cover Cambridge and Waterloo. |
| Hosting | Emergent allows one custom domain per deployment; full multi-domain use needs hosting where you control the domains. |
