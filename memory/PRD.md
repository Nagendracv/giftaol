# giftaol.ca — PRD

## Original problem statement
giftaol.ca Requirements (v0.11): word-of-mouth gift app for Art of Living (AOL). A Gift Giver pays a chosen amount (configurable min/max) and receives a 16-character gift code by email, which they pass to a Recipient who enters it during AOL course registration in Harmony. Includes email + one-time code auth with Cloudflare Turnstile, password login, Google sign-in, landing page editable by admins (EN/FR), gift purchase with placeholder (demo) payment, gift code rules (reusable until balance 0, wrong-entry lock), Resend emails (gift, redemption), dashboard, admin menu (content editor, config, Harmony API key), Harmony lookup/redeem APIs (idempotent on harmony_ref), EN/FR everywhere, legal pages (PIPEDA / Quebec Law 25 drafts), Hack Monitor admin page (IP, referrer, URL, status code), deploy to a public URL. Admins: nagendracv@gmail.com, skandanagendra23@gmail.com. (Full text: see first user message.)

User choices: Emergent-managed Google login; Emergent managed email (Resend); Turnstile test keys for now; Hack monitor logs every visit and API call; style like artofliving.org/ca-en; user will supply a logo later; French support.

## Architecture
- Backend FastAPI: core.py (db, hashing, JWT cookie, rate limits, config), emailer.py (managed email + guardrail gate + retries + templates), routes_auth.py, routes_gifts.py, routes_harmony.py, routes_admin.py, server.py (hack-monitor middleware, indexes, admin seed), defaults.py (default config + landing content EN/FR).
- Frontend React: lib (api, i18n, auth, site, legal), pages (Landing, Login, AuthCallback, Dashboard, NewGift, GiftDetail, Admin, Legal), components (Header, Layout, Turnstile, GiftBits, admin/*).
- MongoDB collections: users, email_verifications, code_request_log, login_attempts, gifts, redemptions, payments, harmony_keys, harmony_calls, request_logs (30-day TTL), app_config, landing_content, landing_content_versions.
- Amounts stored as integer cents.

## Implemented (2026-11-14)
- Auth: email code (6-digit, hashed, no expiry, 10 wrong tries discards it, 5 requests/day/email), password login with Turnstile + lockout, Emergent Google login (creates local user), JWT httpOnly session, next-redirect, change/set password.
- Gift flow with DEMO payment (env DEMO_PAYMENTS_ENABLED + admin payment mode), code generation, gift email with banner/next steps/security notice, confirmation page with Copy, dashboard with masked codes, statuses, redemptions, resend email (3/hour).
- Harmony API with X-Harmony-Key (hashed, rotate/revoke, shown once), idempotent redeem, wrong-entry lock (prefix-8 match) + admin unlock, redemption email.
- Admin: landing content editor EN/FR with rollback, config page, hack monitor.
- Legal drafts EN/FR, EN/FR switcher (browser default, saved).
- Deviation: Google users get a welcome email (not a plaintext password) due to email-safety rules; they set a password in Account or via the email-code flow.

## Backlog
- P0: Real Turnstile keys + real payment provider (Zeffy) via verified webhook; set DEMO_PAYMENTS_ENABLED=false in production; user logo.
- P1: Admin screens translated to French; mobile card layout for Hack Monitor; explicit CORS origins; persistent (DB) rate limits.
- P2: Signed Harmony requests; admin management screen; object storage for images.

## Next tasks
- Receive logo and place in header; deploy; owner sets production secrets.
