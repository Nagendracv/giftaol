# Multi-City Art of Living Sites — Phase 1 Plan

One web application serves many city websites. The web address a visitor uses decides which city's site they see, with its own logo, in English or French.

## Who it's for
- **Visitors** to a city site (e.g. aolottawa.ca) who want to see that city's Art of Living offerings.
- **Registered users** who sign in. For now they see a "coming up" dashboard.
- **Admins** (first admin: nagendracv@gmail.com) who manage site mapping, logos, translations and other admins, and who review visit logs.

## Core features and experience
**City resolution (as in your requirements, sections 4.1, 4.2, 4.5–4.7)**
- Each web address (host, plus port when it isn't the default) maps to exactly one city. The match ignores upper/lower case and a trailing dot. `www.` addresses match only when they are listed.
- Startup fails with a clear message if one host is listed under two cities, a city ID appears twice, or a nearby city doesn't exist.
- An unknown host gets HTTP 404 with a neutral "This site is not configured" page, and a warning is logged.
- `/healthz` answers 200 for any host.
- Every request log line includes the resolved city (or `unknown`).
- Local config maps `localhost:5623 → Ottawa` and `localhost:5624 → Mississauga`. The preview address in this workspace is also mapped to Ottawa, so the demo works here.
- Host resolution is a separate, unit-tested function covering every case listed in AC-13.

**Public city site (pages are rendered on the server)**
- A simple page with a header:
  - Top left: the default Art of Living logo, unless the city tied to the current web address has its own logo in config.
  - Top right: an English / French switcher and a "Sign up / Log in" button.
- The page body reads `hello <city>`, e.g. "hello ottawa". The word "hello" comes from the language file, so French shows the French text.

**Sign up / Log in**
- Email and password, or "Continue with Google".
- Forgot-password and email verification are included.
- One account works on every city site.

**After sign-in**
- Regular users see a dashboard that says "Coming up".
- Admins see the same dashboard plus an admin menu:
  1. **Access logs:** every visit, showing time, visitor IP, the site address used, the page requested, and the matched city (or unknown). Admins can filter by city or host and browse page by page.
  2. **Site configuration:** add and edit cities and their hosts, display name, time zone, nearby cities, contact details, default language and logo upload. Changes apply right away with no restart, and they are checked by the same rules that run at startup.
  3. **Text & languages:** edit every user-facing text in English and French side by side.
  4. **Users & admins:** list users and promote or demote admins. At least one admin always remains.

## User flow
1. A visitor opens aolottawa.ca and sees the Ottawa logo, the language switcher, the login button and "hello ottawa".
2. The visitor switches to French and the text changes. The choice is remembered on that browser.
3. The visitor clicks "Sign up / Log in" and signs up with email or Google, then lands on the "Coming up" dashboard.
4. An admin signs in, sees the admin menu, and uses it to check visit logs, add a new city with its host and logo, edit texts, or promote another user.
5. A visit to an address that isn't configured gets the 404 page, and the visit is still logged.

## UI/UX feel
Clean, calm and minimal, with plenty of white space. The header holds a logo, the language switcher and a login button. Admin screens use simple tables and forms. Pages are readable on phones and aim for accessible contrast and keyboard use (WCAG 2.1 AA).

## Implementation phases
**Phase 1 — MVP (built now)**
- Host-to-city mapping, validation and the unit-tested resolver
- 404 page for unknown hosts, `/healthz`, and logs that carry the city
- Server-rendered home page with header, per-site logo, EN/FR switcher and `hello <city>`
- Email/password and Google sign-in, the "Coming up" dashboard and admin roles
- Admin: access logs, site configuration with logo upload, text editor for both languages, users & admins
- Local git repository with small commits and no remote

**Phase 2 — Courses (later)**
- Decide where course data comes from
- Course listings and detail pages scoped to the city plus its nearby cities, with nearby courses labelled
- No cross-city leakage, draft/cancelled/past courses hidden, times shown in the city's time zone (AC-7 to AC-10)

**Phase 3 — Growth (later)**
- Per-city SEO: title, canonical URL, sitemap
- Optional redirect for unknown hosts
- A course admin screen, if course data is managed in the app

## Assumptions
- **Config:** the JSON file in the repo is the starting configuration. After first startup, admin edits saved in the app take over. A separate local-dev JSON file can override the default one.
- **Admin list:** admin access is stored separately from the site mapping, as you asked. nagendracv@gmail.com becomes admin on first sign-in once the email is verified.
- **Sign-in service:** login runs on Emergent's managed sign-in service, which covers email/password and Google. Users made in the preview are separate from users on the live site.
- **Sign-in page:** this screen uses the service's ready-made form rather than a custom-built one. Everything else is rendered on the server.
- **Logins across sites:** you sign in on each site address separately. The account is the same, but being logged in on one domain doesn't log you in on another.
- **Default language:** a site opens in its city's default language (English unless set otherwise). The visitor's own choice overrides it.
- **French texts:** French starts as a copy of the English text until an admin translates it.
- **Logos:** every site uses the Art of Living logo you supplied (sun with two swans, "THE ART OF LIVING") by default. If a city's config names a logo, either in the file or uploaded from the admin screen, that logo replaces the default on that city's site.
- **Access logs:** logs are kept for 90 days.
- **Visit log scope:** every page visit is logged, including unknown hosts. Health checks and image/style files are not logged.
- **Proxy headers:** the forwarded host header is trusted only when the setting is on. It is on for the preview environment, which sits behind a proxy.
- **Mississauga demo:** the localhost:5624 → Mississauga case is proven by automated tests, because only one preview address exists here.
