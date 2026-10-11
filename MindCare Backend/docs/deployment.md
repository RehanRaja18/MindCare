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
| `CORS_EXTRA_ALLOWED_ORIGINS` | optional, comma-separated extra browser origins on top of the Vercel origin, e.g. `http://localhost:5000` for a local Flutter web demo. Unset normally; remove after a demo |
| `AI_SERVICE_URL` | the MindCare AI service's base URL, no trailing `/predict` (e.g. `https://mindcare-api-fysd.onrender.com`). Unset → `POST /api/v1/ai/anxiety-prediction/` answers 503 |

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

`config/settings/prod.py` allows the MindCare Web frontend,
`https://mind-care-web-seven.vercel.app`, plus any origins in the optional
`CORS_EXTRA_ALLOWED_ORIGINS` env var (unset normally; e.g. `http://localhost:5000`
for a local Flutter web demo, removed afterwards). `CORS_ALLOW_CREDENTIALS=False`
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
      5/min, register 10/hour, reference 120/min, stats 60/min). Measure it with the
      temporary `GET /api/v1/accounts/debug/client-ip/` (admin JWT): set
      `NUM_PROXIES` to the number of `X-Forwarded-For` entries that are proxies,
      i.e. the value for which `throttle_ident` equals your own public IP (normally
      the same as `cf_connecting_ip`). Then remove the endpoint in the next PR
      (see @decisions.md, 2026-10-10).
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

## Demo accounts

`DEMO_PASSWORD=<choose one> python manage.py seed_demo` creates 6 approved demo
psychologists and 2 demo patients (all `demo.*@example.com`; psychologist bios start
"Demo account, not a real psychologist."; names are plain because of the name rule). It
can be re-run safely. Demo patient 1 (Hina) has an accepted relationship with
Dr. Sara Ahmed and demo patient 2 (Daniyal) a pending request to her, so
`demo.psych.sara@example.com` shows both the inbox and the patient list. Pending
requests expire after 3 days; re-running the command renews it. `python manage.py seed_demo --remove` deletes exactly those
accounts and their relationship rows. Render's free tier has no Shell, so run it
locally with `DATABASE_URL` set to the production URL for that one command, then
remove the variable again. Demo cities outside Pakistan
(London, Dubai) are created unverified, like any typed city.

## Removing test data (Phase 3 onwards)

`CareRelationship` rows reference profiles with `on_delete=PROTECT`, so a user who
has relationship rows **can't be deleted from Django admin**. To remove test
accounts, delete in this order, scoped to the test users' ids (replace `<ids>`):

```sql
-- 1. relationship rows first (PROTECT blocks everything else otherwise)
DELETE FROM relationships_carerelationship
 WHERE patient_id IN (SELECT id FROM patients_patientprofile WHERE user_id IN (<ids>))
    OR psychologist_id IN (SELECT id FROM psychologists_psychologistprofile WHERE user_id IN (<ids>));
-- 2. profiles (psychologist M2M rows and NGO service areas cascade)
DELETE FROM patients_patientprofile WHERE user_id IN (<ids>);
DELETE FROM psychologists_psychologistprofile WHERE user_id IN (<ids>);
DELETE FROM ngo_ngoprofile WHERE user_id IN (<ids>);
-- 3. users
DELETE FROM accounts_user WHERE id IN (<ids>);
```

Check the ids with a `SELECT` first, and run it inside a transaction
(`BEGIN; … COMMIT;`) so a mistake can be rolled back.

## Supabase settings

- **Data API: OFF** (turned off 2026-10-10). Django never used it, and with it on,
  any table without RLS was readable with the anon key. Keep it off; see
  @decisions.md, 2026-10-10.

## Security headers

- **HSTS:** `prod.py` sends `Strict-Transport-Security: max-age=86400` (one day).
  After a week with no HTTPS problems, raise `SECURE_HSTS_SECONDS` to `31536000`.

## TODO

- [ ] **Supabase heartbeat workflow**: a scheduled GitHub Actions job that makes a
      lightweight query at least every few days, so the free-tier project is never
      paused. Not implemented yet. Until it is, a 7-day quiet period (e.g. between
      demos or over a break) takes the database offline.
- [ ] Celery worker as a separate Render service (first needed in Phase 7).
