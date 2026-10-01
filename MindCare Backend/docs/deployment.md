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

**Local development:** the developer's local `.env` `DATABASE_URL` points at the
local docker Postgres (switched 2026-09-30); production credentials live only in
Render. Keep it that way: tests are guarded against remote databases (see
@decisions.md, 2026-09-28), but `runserver`, `migrate` and `dbshell` use
`DATABASE_URL` as-is.

**Supabase password resets:** after resetting the Supabase database password,
update `DATABASE_URL` on Render to match. On 2026-09-30 a stale `DATABASE_URL`
after a reset caused `/admin/` 500s and a failed deploy (not caused by Phase 2
code). It was fixed by updating the variable on Render.

`JWT_SIGNING_KEY` is not set, so JWTs are signed with `SECRET_KEY` (see
`config/settings/base.py`).

### CORS

`config/settings/prod.py` allows exactly one browser origin, the MindCare Web
frontend: `https://mind-care-web-seven.vercel.app`. `CORS_ALLOW_CREDENTIALS=False`
(JWT bearer auth, no cookies). The local Vite origin is allowed only in `dev.py`.

**Status:** shipped to `main` in PR #17 (`backend-cors-and-prod-pins`). Before it
merged, a preflight against the live service (2026-09-27) returned `200` with no
`Access-Control-*` headers. Re-check after each deploy that
`OPTIONS /api/v1/accounts/login/` with `Origin: https://mind-care-web-seven.vercel.app`
returns `Access-Control-Allow-Origin` for that origin.

### Known tradeoffs (free tier)

- **Cold starts:** Render's free instances spin down after ~15 min without traffic.
  The next request waits for a cold start (~50s documented; ~36s measured on
  2026-09-27). Frontends should show a loading state rather than time out quickly.
- **Supabase inactivity pause:** Supabase free-tier projects are paused after
  **7 days** without activity, which takes the production database offline until
  someone manually restores it.

## Pre-deploy checklist for the Phase 2 merge

Status 2026-09-30: migrations-on-deploy, existing users and frontend readiness are
done. **Still open before merging:** `NUM_PROXIES` on Render.

- [ ] **Rate limits behind Render's proxy:** `NUM_PROXIES` defaults to 0, so DRF
      throttles on the proxy's address and every user shares one bucket (login
      5/min, register 10/hour, reference 120/min, stats 60/min). Confirm Render's
      proxy hop count and set `NUM_PROXIES` (likely `1`) in Render's environment,
      then re-test that a throttle is per-client.
- [x] **Migrations run on deploy** (confirmed from Render's dashboard,
      2026-09-30). Render's build command:
      `pip install -r requirements/prod.txt && python manage.py collectstatic --noinput && python manage.py migrate`.
      The Phase 2 migrations (reference 0001–0003, accounts 0002, patients/
      psychologists/ngo 0001) apply automatically on the deploy after the merge.
- [x] **Existing production users** (checked 2026-09-30): only the admin account
      remains. The one test account was deleted directly in Supabase. No
      patient/psychologist/NGO user exists without a profile.
- [x] **Frontend readiness** (2026-09-30): the register body is a breaking change
      (`is_adult_confirmed` + nested `profile`). Both the Web and App teams have
      reviewed the new contract. MindCare Web's signup is built on its own branch
      and ships after this backend is live, so it is tested against the real
      backend. Until each frontend ships its signup, any old-format register
      request gets a 400.
- [ ] **After deploy:** re-run the CORS preflight check (see CORS section) and
      check `/api/docs/` shows the register and `/me/` contracts.

## TODO

- [ ] **Supabase heartbeat workflow**: a scheduled GitHub Actions job that makes a
      lightweight query at least every few days, so the free-tier project is never
      paused. Not implemented yet. Until it is, a 7-day quiet period (e.g. between
      demos or over a break) takes the database offline.
- [ ] Celery worker as a separate Render service (first needed in Phase 7).
