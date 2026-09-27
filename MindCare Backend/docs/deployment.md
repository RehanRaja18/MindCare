# Deployment

Production backend runs on **Render**, with **Supabase** (Postgres) and
**Redis Cloud** (Redis). See @decisions.md for why these providers were chosen.
**No secrets belong in this file.** Values live only in Render's dashboard.

## Render (live)

- **URL:** https://mindcare-ajri.onrender.com (API under `/api/v1/`, docs at `/api/docs/`)
- **Instance tier:** free.
- **Settings module:** `DJANGO_SETTINGS_MODULE=config.settings.prod`.
- **Production superuser:** a real production superuser account exists (created
  via `createsuperuser`, so `is_super_admin=True`). Its credentials are not
  recorded in the repo.

### Environment variables (configured in Render)

| Variable | Value / source |
|----------|----------------|
| `DATABASE_URL` | Supabase **connection pooler** URL, with `sslmode=require` |
| `REDIS_URL` | Redis Cloud instance |
| `SECRET_KEY` | generated fresh for production; not shared with any dev `.env` |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `ALLOWED_HOSTS` | `.onrender.com` |

`JWT_SIGNING_KEY` is not set, so JWTs are signed with `SECRET_KEY` (see
`config/settings/base.py`).

### CORS

`config/settings/prod.py` allows exactly one browser origin, the MindCare Web
frontend: `https://mind-care-web-seven.vercel.app`. `CORS_ALLOW_CREDENTIALS=False`
(JWT bearer auth, no cookies). The local Vite origin is allowed only in `dev.py`.

**Status (2026-09-27): not yet live.** The CORS commits are on `backend-work` and
not merged to `main`. A preflight against the live service returned `200` with no
`Access-Control-*` headers. CORS takes effect once `backend-work` is merged and
Render redeploys.

### Known tradeoffs (free tier)

- **Cold starts:** Render's free instances spin down after ~15 min without traffic.
  The next request waits for a cold start (~50s documented; ~36s measured on
  2026-09-27). Frontends should show a loading state rather than time out quickly.
- **Supabase inactivity pause:** Supabase free-tier projects are paused after
  **7 days** without activity, which takes the production database offline until
  someone manually restores it.

## TODO

- [ ] **Supabase heartbeat workflow**: a scheduled GitHub Actions job that makes a
      lightweight query at least every few days, so the free-tier project is never
      paused. Not implemented yet. Until it is, a 7-day quiet period (e.g. between
      demos or over a break) takes the database offline.
- [ ] Merge `backend-work` so CORS (and Phase 2) reach production.
- [ ] Celery worker as a separate Render service (first needed in Phase 7).
- [ ] Pin `gunicorn` in `requirements/prod.txt` (currently unpinned).
