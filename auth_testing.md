# Auth testing notes (giftaol.ca)

- Google sign-in uses Emergent Auth: frontend redirects to https://auth.emergentagent.com/?redirect=<origin>/dashboard,
  returns with #session_id=..., frontend POSTs /api/auth/google {session_id}; backend fetches
  https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data and issues our own JWT cookie `access_token`.
- To simulate a logged-in user in browser tests: log in via POST /api/auth/login (password + dummy turnstile token)
  or create a JWT. Cookie: access_token, httpOnly, secure, SameSite=None, path=/.
- Password users: bcrypt hash ($2b$). Lockout: 5 failed logins per ip:email -> 15 min.
- Collections: users (custom `id` field, never `_id`), email_verifications, code_request_log, login_attempts.
