# Here are your Instructions

> **Visible: Art of Living in AI search** is a separate tool kept in this repo under [`visible/`](visible/). It is not part of the city website.
> Live demo: https://brahmaan-space.github.io/Visible/ · Source: https://github.com/Brahmaan-space/Visible · Run it: `cd visible && npm install && npm start`

## Multi-city sites (Phase 1)
- Cities and hosts: `backend/config/sites.json` (prod) / `backend/config/sites.local.json` (local), selected by `SITE_CONFIG_FILE`.
- Texts: `backend/locales/<lang>.json`; add a file + list it in `locales` to add a language.
- Run standalone on the milestone port: `cd backend && uvicorn server:app --port 5623` then open http://localhost:5623/ → `hello ottawa`.
- Tests: `cd backend && python -m pytest tests/test_site_config.py tests/test_app.py -n 0`.
