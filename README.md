# Here are your Instructions

## Multi-city sites (Phase 1)
- Cities and hosts: `backend/config/sites.json` (prod) / `backend/config/sites.local.json` (local), selected by `SITE_CONFIG_FILE`.
- Texts: `backend/locales/<lang>.json`; add a file + list it in `locales` to add a language.
- Run standalone on the milestone port: `cd backend && uvicorn server:app --port 5623` then open http://localhost:5623/ → `hello ottawa`.
- Tests: `cd backend && python -m pytest tests/test_site_config.py tests/test_app.py -n 0`.
