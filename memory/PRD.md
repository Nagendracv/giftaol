# PRD: Multi-City Art of Living Course Sites

## Original problem statement
One web app serves many city sites. The request host (with any non-default port) maps to one city through configuration. Phase 1: the home page says `hello <city>`, unknown hosts get a 404, `/healthz` works for any host, all text comes from locale files (EN now, FR-ready), and work is kept in a local git repo. Phase 2 (courses, listings, nearby, SEO) comes later. The full requirements are in the user's first message (rev. 2, 2026-11-14).

Approved plan additions: a header (per-city logo, EN/FR switcher, Sign up / Log in), Clerk sign-in (email/password + Google), a "Coming up" dashboard, and admin screens for access logs, site configuration with logo upload, EN/FR texts, and users & admins. The first admin is nagendracv@gmail.com.

## Architecture
- FastAPI backend (`backend/`):
  - `site_config.py` holds the pure resolver and validation.
  - `server.py` has the middleware that resolves the city, the server-rendered `/`, `/healthz` and `/api/site`.
  - `admin_routes.py`, `roles.py` (Clerk roles) and `pages.py` (HTML).
  - MongoDB collections: `site_config` (the admin override), `text_overrides`, `access_logs` (90-day TTL), `users` and `files`.
  - Logos are kept in Emergent Object Storage.
- Config: `backend/config/sites.json` (production) and `sites.local.json` (local/preview), chosen with `SITE_CONFIG_FILE`. Once an admin saves, the DB copy takes over. "Reset to file" brings the file back.
- Locales: `backend/locales/en.json` and `fr.json`. They are re-read when they change on disk, and admin overrides are layered on top.
- React SPA (`frontend/`) for /sign-in, /sign-up, /dashboard and /admin/*. `setupProxy.js` sends `/`, `/healthz` and `/api` to the backend and keeps the Host header. The SPA calls a relative `/api` so the host decides the city.
- Tests: `backend/tests/test_site_config.py` and `test_app.py` (28 tests, covering AC-1 to AC-6 and AC-11 to AC-14).

## Implemented (2026-11-14)
- Host to city resolution: case-insensitive, trailing dot ignored, default ports stripped, non-default ports kept, `www.` only when listed. X-Forwarded-Host is used only when TRUST_PROXY is set.
- Startup fails with a clear list of problems (duplicate host or cityId, unknown nearby city, bad timezone or locale).
- Unknown host gives a 404 page and a warning. A redirect option is in config. `/healthz` works for any host, and log lines include `cityId=`.
- Server-rendered home with logo, EN/FR switcher (remembered in a cookie) and `hello <city>`.
- Clerk auth, the "Coming up" dashboard and admin roles (ADMIN_EMAIL).
- Admin screens: access logs with filters and paging, site config with live validation and logo upload, EN/FR text editor, and users & admins (always keeps one admin).
- Local git commits, no remote.

## Implemented (2026-11-14, iteration 2): Courses
- The home page shows Newcomer (default), Advanced and Online tabs filled from the Unity courses API. It makes one combined Canada-wide request covering every listed mctype (`config/programs.json`). The cache fills on first use and lasts COURSE_CACHE_MINUTES=60. Paging stops past the furthest window, and after a failure the app waits 2 minutes before retrying.
- Each city has its own centre point and area: `latitude`, `longitude`, `radiusKm` (default 50) and `monthsAhead` (default 2), all validated and editable in the admin. The in-person tabs filter by distance and date. The online tab lists organisers within the radius first.
- Courses expand inline to show schedule, venue, teachers, fees, language, contact and a Register link. All labels and date formats come from the EN/FR locale files.

## Implemented (2026-11-15, iteration 3): Rev 3 + Visit insights
- Distance dropdown (10/25/50/100/200 km, remembered) and program filter (?program=slug).
- (2026-11-15) Near me (IP) was replaced by an editable city picker (?place=, cookie) with ~515 Canadian places over 15k people from GeoNames (config/canadian_cities.json, credited in the footer), plus an Apply button. It defaults to the site's city, and no IP geolocation is used.
- Header shows "Art of Living <City>"; footer with Privacy/Terms and the GeoNames credit; /privacy and /terms (EN/FR, admin-editable); cookie notice.
- Course cards: Register, .ics download (one event per session), Google Calendar link, Share, shared links /?course=id (opens expanded, og: tags).
- French course titles from the fr-ca feed (separate hourly cache, matched by id).
- Reminder emails (Emergent managed Resend): double opt-in (the confirm page needs a POST), reminder ~24h before start, cancel link, hourly cron .emergent/crons.yml -> /api/cron/hourly.
- Visit insights: insight_events (90-day TTL) and /admin/insights with tab views and top courses per city.

## Backlog
- P1: course titles stay in English (the feed uses language=en-ca); a French feed (fr-ca) may be possible.
- P2: course search or filter by program within a tab.
- P2: per-city SEO (title, canonical URL, sitemap) and a course admin screen.
- P2: the server-rendered home always shows "Sign up / Log in", even when signed in. Signed-in users who click it are sent on to the dashboard.
- Note: in a production build, `/` may be served by the SPA fallback (same text, but no real 404 status) unless routing sends `/` to the backend.

## Implemented (2026-11-15, iteration 6-7): Give a gift
- Header "Give a gift" link on every city site (server and SPA) -> /gift (mockup design: serif heading, presets, message 500, recipient name, how-used box).
- Guest: own email + Cloudflare Turnstile (TEST keys until real ones are supplied) -> 6-digit email code -> /gift/:id verify page (2/3). If the email already has an account: note + "Verification code" / "My password" tabs. Code or password signs the user in at once (Clerk ticket / password + /claim); account auto-created for new emails; admins are never auto-signed in.
- Signed-in: straight to payment. DEMO payment page (3/3) with Zeffy/Stripe/PayPal note; Pay creates payment record (provider=demo) and the gift code (16 chars, no 0/O/1/I, groups of 4, unique).
- Confirmation: registered banner, demo note, code, Copy (security dialog), next steps; gift email via Emergent managed email with retries (5/20/60s) + hourly cron retry of failed emails.
- Dashboard: My gifts (masked code + reveal, balance, status, uses, resend email 10-min cooldown / 5 per day, detail page /gifts/:id), Account (email, change password, log out).
- Harmony API (open, demo): GET /api/gift-codes/{code}, POST /api/gift-codes/{code}/redeem {amount, courseName, courseReference}; idempotent per courseReference; rejected redeems count as wrong entries -> lock at cap (default 5) -> 423; redemption email to giver.
- Admin /admin/gifts: min/max/cap/quick amounts, codes table with search, unlock, revoke, API reference. All texts EN/FR (gift* keys) editable in Text & languages.
- Collections: gifts, gift_checkouts (7-day TTL), gift_payments, gift_redemptions, gift_settings, gift_failed_lookups.

## Backlog (gifts)
- Real payment provider (Zeffy/Stripe/PayPal) with webhook-confirmed code creation.
- Real Turnstile keys (TURNSTILE_SITE_KEY / TURNSTILE_SECRET_KEY).
- API key for Harmony calls before going live.
