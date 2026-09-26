# Design: Phase 2 — Profiles, Patient Privacy, Reference Data, Public Stats

**Date:** 2026-09-26
**Status:** Draft — awaiting user review
**Branch:** `backend-work`
**Apps:** `apps/patients`, `apps/psychologists`, `apps/ngo`, new `apps/reference`,
new `apps/stats`; changes to `apps/accounts`, `core/audit.py`, `config/`.

Every requirement below was settled in the Phase 2 requirements interview and is
recorded with its reasoning in @../../decisions.md (entries dated 2026-09-26). This
spec says *how* to build them; `decisions.md` says *why*. Where the two ever
disagree, stop and ask — do not pick one silently.

## 1. Purpose

Give every patient, psychologist and NGO account a role-specific profile, created
atomically with the account; ship the patient privacy system (pseudonym + public
flag + a single display-identity selector); add shared, admin-editable reference
data (countries, cities, languages, specializations); and serve the
`GET /stats/public/` endpoint MindCare Web already calls. Phases 3–15 build on these
profiles.

## 2. Scope

**In scope**
- `PatientProfile`, `PsychologistProfile`, `NGOProfile` (+ `NGOServiceArea`) models.
- Profile creation inside `register_user()` in one transaction; nested,
  role-dependent `profile` object in the register request.
- 18+ self-declaration on all public registrations (`User.adult_confirmed_at`).
- Owner-only `GET`/`PATCH` "my profile" endpoints for each of the three roles.
- Credential-field lock on psychologist/NGO profile updates.
- Patient pseudonym + `is_profile_public` + `get_patient_display_identity()`, with
  `identity_reveal` audit logging for admin resolutions of private profiles.
- `apps/reference`: `Country`, `City`, `Language`, `Specialization` models, seed data
  migrations, public read-only list endpoints, city get-or-create service.
- `apps/stats`: `GET /api/v1/stats/public/`, anonymous-throttled, ~5 min cache.
- Django admin registration for all new models.
- Service, selector and API tests; `module-reference.md`, `architecture.md`,
  `decisions.md` updates.

**Explicitly out of scope (owner in parentheses)**
- Admin-facing profile API endpoints, approval endpoints, credential re-review flow,
  document uploads, avatars (Phase 2.5).
- Psychologist directory, patient ↔ psychologist access, assigned-psychologist
  identity exception, switching `people_in_care` to accepted patients (Phase 3).
- Any clinical/health field on any profile (Phase 5).
- Consultation fee (Phase 9). Email/phone verification, phone-number login
  (Phase 10 / unscheduled).
- Community display, outing-matching demographics query, creator precondition
  (Phase 11). Emergency contacts, NGO support types (Phase 13).
- Minors (out of scope for the product; see decisions.md).
- New third-party packages — **none are added by this phase.**

## 3. `apps/reference` — shared reference data

New Django app, mounted at `/api/v1/reference/` (added to `API_V1_APPS` and
`INSTALLED_APPS`). Owns all four tables so there is one admin-maintained reference
area with one pattern.

### 3.1 Models

| Model | Fields | Constraints / notes |
|-------|--------|---------------------|
| `Country` | `code` (CharField 2, ISO 3166-1 alpha-2, unique), `name` | Seeded, all ISO 3166-1 countries. |
| `City` | `country` (FK Country, PROTECT), `name` (CharField 120) | `UniqueConstraint(Lower("name"), "country")` — unique per country ignoring case. |
| `Language` | `code` (CharField 2, ISO 639-1, unique), `name`, `is_active` (default True) | Seeded, ISO 639-1. |
| `Specialization` | `slug` (unique), `name`, `is_active` (default True) | Seeded with the **placeholder** list (see decisions.md). |

`is_active=False` hides an entry from list endpoints and rejects it for *new*
assignments; existing profiles that reference it are untouched. FKs from profiles to
reference rows use `on_delete=PROTECT`, so a referenced row cannot be deleted.

### 3.2 Seed data

Stored in the repo as JSON under `apps/reference/data/` (`countries.json`,
`languages.json`, `pakistan_cities.json`, `specializations.json`) and loaded by data
migrations (`RunPython`, with a reverse that deletes only the seeded rows).
- Countries: full ISO 3166-1 list (~249).
- Languages: full ISO 639-1 list (~184).
- Cities: major Pakistani cities (~30: all provincial capitals and cities over
  ~500k population, plus Islamabad/Rawalpindi, Gilgit, Muzaffarabad).
- Specializations: anxiety, depression, trauma / PTSD, couples / relationship,
  grief, addiction / substance use, stress management, OCD, eating disorders, sleep
  issues, anger management, family therapy. **Placeholder pending clinical-advisor
  review.**

### 3.3 Services / selectors

- `reference.services.resolve_city(*, country, name) -> City` — normalizes `name`
  (strip, collapse internal whitespace), matches case-insensitively within
  `country`, creates the row if absent. Race-safe: on `IntegrityError` from the
  unique constraint, re-fetch. Empty name after normalization → validation error.
  Max length 120.
- `reference.selectors`: `list_countries()`, `search_cities(*, country_code,
  search=None, limit=20)` (case-insensitive prefix match, ordered by name),
  `list_languages()`, `list_specializations()` (active only).

### 3.4 Endpoints (all `AllowAny`, `AnonRateThrottle` scope `reference`, read-only)

Public because registration forms need them before the user has an account.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/reference/countries/` | `[{code, name}]` |
| GET | `/api/v1/reference/cities/?country=PK&search=lah` | `[{id, name, country}]`, max 20; `country` required (400 without it) |
| GET | `/api/v1/reference/languages/` | `[{code, name}]` (active) |
| GET | `/api/v1/reference/specializations/` | `[{slug, name}]` (active) |

There is **no public city-create endpoint.** Cities are created only as a side
effect of a profile write through `resolve_city()`, which is already rate-limited by
registration (10/hour) or requires authentication.

## 4. `apps/accounts` changes

### 4.1 `User.adult_confirmed_at`

New nullable `DateTimeField`. Set to `now()` by `register_user()`. Existing rows and
`createsuperuser` accounts stay `NULL` (the declaration is a public-registration
requirement). Migration is additive.

### 4.2 Register request (contract change for both frontends)

`POST /api/v1/accounts/register/` — same path, bigger body:

```json
{
  "email": "...", "password": "...", "full_name": "...",
  "role": "patient | psychologist | ngo",
  "is_adult_confirmed": true,
  "profile": { ...role-specific, see below... }
}
```

- `is_adult_confirmed` must be literally `true`; anything else → 400.
- `profile` is validated by a role-specific serializer:
  - **patient:** `{ "timezone": "Asia/Karachi" }` — `timezone` required (sent by the
    device, not typed by the user). All other patient fields are filled in later.
  - **psychologist:** all required fields from §6.1.
  - **ngo:** all required fields from §7.1, including `service_areas` (≥1).
- `admin` stays rejected (unchanged).
- Response 201: existing `UserPublicSerializer` fields plus `profile` (the role's
  owner-view serializer, §5.4/§6.3/§7.3). No tokens (unchanged).

### 4.3 `register_user()` orchestration

`register_user(*, email, password, full_name, role, profile_data)`:

```
with transaction.atomic():
    user = User.objects.create_user(..., adult_confirmed_at=now())
    if role == PATIENT:      patients.services.create_patient_profile(user=user, **profile_data)
    elif role == PSYCHOLOGIST: psychologists.services.create_psychologist_profile(user=user, **profile_data)
    elif role == NGO:        ngo.services.create_ngo_profile(user=user, **profile_data)
log_auth_event("register", ...)   # after commit succeeds, unchanged fields
```

- Any exception inside the block rolls back the `User` too — no user without a
  profile, ever. **No Django signals** (see decisions.md).
- Profile services raise domain exceptions (e.g. `DuplicateLicenseError`,
  `DuplicateNGORegistrationError`, `ProfileValidationError`); the view maps them to
  400 with non-revealing messages.
- Uniqueness races (license / NGO registration number) are caught as
  `IntegrityError` inside the profile service and re-raised as the domain error, the
  same pattern as `DuplicateEmailError`.

## 5. `apps/patients`

### 5.1 `PatientProfile`

| Field | Type | Notes |
|-------|------|-------|
| `user` | OneToOne → User, CASCADE, `related_name="patient_profile"` | |
| `pseudonym` | CharField 16, unique, not editable | `Patient-` + `secrets.token_hex(3)`; immutable |
| `is_profile_public` | Bool, default False | |
| `country` | FK Country, null | required once set; can't be cleared back to null |
| `city` | FK City, null | must belong to `country` |
| `timezone` | CharField 64 | IANA name, validated against `zoneinfo.available_timezones()` |
| `date_of_birth` | Date, null | if set: must be ≥ 18 years before today, not in the future |
| `gender` | CharField choices, null | `female`, `male`, `other`, `prefer_not_to_say` |
| `phone_number` | CharField 20, null | E.164-style regex (`^\+[1-9]\d{6,14}$`). **Model comment:** contact number only — not a login identifier; phone login would be a separate unique, verified field on `User` (see decisions.md). |
| `preferred_language` | FK Language, null | active languages only for new assignments |
| `created_at` / `updated_at` | auto | |

No bio, no avatar, no clinical fields (decisions.md, Phase 2 PHI line).

### 5.2 Services

- `create_patient_profile(*, user, timezone)` — generates the pseudonym; on
  pseudonym `IntegrityError` retries with a fresh one inside a savepoint, up to 5
  attempts, then raises. Asserts `user.role == patient`.
- `update_patient_profile(*, profile, **fields)` — allowed fields: `is_profile_public`,
  `country`, `city` (as a name, resolved via `reference.resolve_city`),
  `timezone`, `date_of_birth`, `gender`, `phone_number`, `preferred_language`.
  `pseudonym` is never accepted. City without a country (existing or in the same
  request) → error.

### 5.3 Selector: `get_patient_display_identity(*, patient_profile, viewer)`

Returns `{"display_name": str, "is_real_name": bool}`. **Never returns gender, date
of birth, city, or anything else** (decisions.md, demographics rule). Rules, first
match wins:

1. `viewer` is the patient themself → real name.
2. `is_profile_public` → real name.
3. `viewer` is the patient's assigned psychologist → real name, not logged.
   **Phase 2 stub:** `_is_assigned_psychologist()` returns `False` with a comment
   pointing at Phase 3.
4. `viewer.role == admin` → real name, and `core.audit.log_identity_reveal(
   viewer_id=..., patient_id=...)` is emitted (IDs only).
5. Anyone else, including anonymous (`viewer=None`) → pseudonym.

Nothing in Phase 2 calls this selector from an API endpoint (there is no
cross-user profile view yet); it ships tested at the selector level. Phases 3 and
11 must call it (decisions.md).

**Known limitation (Phase 2):** Django admin shows `User.full_name` directly, so
admin access through the Django admin panel is not logged as `identity_reveal`.
Phase 2.5's admin API must route patient identity through this selector.

### 5.4 Endpoints

| Method | Path | Permission | Behaviour |
|--------|------|-----------|-----------|
| GET | `/api/v1/patients/me/` | `IsAuthenticated` + `IsPatient` | Owner view: all §5.1 fields (country/city/language as nested `{code/id, name}`), plus `full_name` |
| PATCH | `/api/v1/patients/me/` | same | Partial update via `update_patient_profile`; `pseudonym` in body → 400 |

API docs for `is_profile_public` state the permanent-disclosure warning
(decisions.md).

## 6. `apps/psychologists`

### 6.1 `PsychologistProfile`

| Field | Type | Req. at registration | Editable after | Visible (Phase 3 directory) |
|-------|------|----------------------|----------------|------------------------------|
| `user` | OneToOne → User | — | — | — |
| `license_number` | CharField 64 | yes | **locked** | **admin only** |
| `license_issuing_country` | FK Country | yes | **locked** | yes |
| `license_issuing_authority` | CharField 200 | yes | **locked** | yes |
| `qualifications` | TextField (max 1000) | yes | **locked** | yes |
| `specializations` | M2M Specialization | yes, ≥1 active | yes | yes |
| `years_of_experience` | PositiveSmallInteger (0–70) | yes | yes | yes |
| `languages` | M2M Language | yes, ≥1 active | yes | yes |
| `country` / `city` / `timezone` | as patient | yes (all three) | yes | yes |
| `gender` | as patient, null | no | yes | yes |
| `bio` | TextField (max 2000), blank | no | yes | yes |

Constraint: `UniqueConstraint("license_issuing_country", "license_number")`.
`license_number` normalized (strip, uppercase) before save so `pmdc-1` and `PMDC-1`
collide.

### 6.2 Services

- `create_psychologist_profile(*, user, **fields)` — validates, resolves city,
  creates profile + M2M rows. Duplicate license → `DuplicateLicenseError` (message:
  "This license is already registered." — no holder details).
- `update_psychologist_profile(*, profile, **fields)` — any credential field in
  `fields` whose value differs from the stored value → `CredentialFieldLockedError`
  (400). Sending an unchanged value is allowed (so clients can PATCH full objects).

### 6.3 Endpoints

| Method | Path | Permission |
|--------|------|-----------|
| GET | `/api/v1/psychologists/me/` | `IsAuthenticated` + `IsPsychologist` |
| PATCH | `/api/v1/psychologists/me/` | same |

Owner view returns all fields including `license_number`. Pending/rejected
psychologists can't log in (Phase 1), so they cannot reach these until approved.

## 7. `apps/ngo`

### 7.1 `NGOProfile` + `NGOServiceArea`

| Field | Type | Req. | Editable after | Visible |
|-------|------|------|----------------|---------|
| `user` (the representative) | OneToOne → User | — | — | — |
| `organization_name` | CharField 200 | yes | **locked** | yes |
| `registration_number` | CharField 64 | yes | **locked** | **admin only** |
| `registration_country` | FK Country | yes | **locked** | yes |
| `registering_authority` | CharField 200 | yes | **locked** | yes |
| `country` / `city` / `timezone` (HQ) | as patient | yes | yes | yes |
| `official_phone` | E.164 as patient | yes | yes | admin only (for now) |
| `official_email` | EmailField | yes | yes | admin only (for now) |
| `website` | URLField, blank | no | yes | yes |
| `description` | TextField (max 2000), blank | no | yes | yes |

Constraint: `UniqueConstraint("registration_country", "registration_number")`,
number normalized as for licenses.

`NGOServiceArea`: `ngo` (FK, CASCADE, `related_name="service_areas"`), `country` (FK
Country), `city` (FK City, null — **null = nationwide**). Two conditional unique
constraints: `(ngo, country)` where `city IS NULL`, and `(ngo, country, city)` where
`city IS NOT NULL` (avoids relying on `NULLS NOT DISTINCT`). City must belong to the
row's country.

Register/PATCH payload shape: `"service_areas": [{"country": "PK"},
{"country": "GB", "city": "London"}]`. On PATCH, a provided `service_areas` list
**replaces** the set (atomic delete + recreate); ≥1 required.

### 7.2 Services

- `create_ngo_profile(*, user, service_areas, **fields)`.
- `update_ngo_profile(*, profile, **fields)` — same credential-lock rule as §6.2.

### 7.3 Endpoints

`GET` / `PATCH` `/api/v1/ngo/me/` — `IsAuthenticated` + `IsNGO`.

## 8. `core/audit.py`

Add `log_identity_reveal(*, viewer_id, patient_id)` emitting one JSON line on the
`mindcare.audit` logger: `{"event_type": "identity_reveal", "timestamp", "viewer_id",
"patient_id"}`. No names, emails or other fields. Kept separate from
`log_auth_event()` so auth events stay a closed set.

## 9. `apps/stats` — `GET /api/v1/stats/public/`

New Django app, no models, mounted at `/api/v1/stats/`.

- `stats.selectors.get_public_platform_stats() -> dict`, cached with
  `cache.get_or_set("stats:public:v1", ..., timeout=300)`:
  - `people_in_care` — count of active users with role `patient`. **Comment in code:
    TEMPORARY interim definition; Phase 3 must switch to patients with an accepted
    psychologist** (decisions.md).
  - `verified_therapists` — active psychologists with `approval_status=approved`.
  - `cities` — distinct `City` ids referenced by the `city` field of any patient,
    psychologist or NGO profile (headquarters). **NGO service areas are not
    counted** — they describe reach, not presence, and a nationwide NGO has none.
    Early undercount of patient cities is expected (decisions.md).
- View: `AllowAny`, `authentication_classes = []`, `AnonRateThrottle` scope
  `public_stats` (`60/min`). Response exactly `{people_in_care, verified_therapists,
  cities}` as integers — matches MindCare Web's contract.

New throttle rates in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`: `reference:
"120/min"`, `public_stats: "60/min"`.

## 10. Django admin

Register every new model. Credential fields are editable **in Django admin only**
(the interim correction path). `pseudonym` is `readonly_fields`. `NGOServiceArea`
as an inline on `NGOProfile`. Reference tables searchable by name.

## 11. Error handling summary

| Situation | Result |
|-----------|--------|
| Missing / false `is_adult_confirmed` | 400 |
| Profile validation failure (any role) | 400, field-level errors; no `User` created |
| Duplicate license / NGO registration number | 400, generic message; no `User` created |
| Credential field changed on PATCH | 400 `credential_field_locked` naming the field |
| `pseudonym` in PATCH body | 400 |
| DOB under 18 / in future | 400 |
| Invalid timezone, phone, inactive language/specialization, city not in country | 400 |
| `/me/` called by another role | 403 |
| Pseudonym collision ×5 | 500 (logged, PHI-free) — practically unreachable at FYP scale |

## 12. Testing plan

Per CLAUDE.md, service-layer tests come first.

- **Service tests** (`tests/test_services.py` in each app):
  - registration creates user + correct profile per role; profile failure rolls
    back the user (assert `User` count unchanged); duplicate license/registration
    number rolls back; `adult_confirmed_at` set.
  - pseudonym format, uniqueness, retry on forced collision, immutability.
  - DOB 18+ boundary (exactly 18 today passes; one day short fails).
  - credential lock: changed value rejected, unchanged value accepted, non-credential
    fields editable.
  - `resolve_city` normalization / case-insensitive reuse / race re-fetch.
  - service-area replace semantics and conditional uniqueness.
- **Selector tests:** display-identity rules 1–5, including that admin on a private
  profile emits exactly one `identity_reveal` with IDs only (assert log contents
  contain no name/email), admin on a public profile emits none, and the result dict
  contains only `display_name` / `is_real_name`. Stats counts, interim
  `people_in_care`, NGO service areas excluded from `cities`, caching.
- **API tests:** register payloads per role (happy + key failures), `/me/` GET/PATCH
  per role and cross-role 403, reference endpoints unauthenticated, stats endpoint
  unauthenticated with exact response keys, throttling scope set.
- **Migration check:** seed migrations apply and reverse cleanly; after `migrate`,
  verify the real schema (tables, unique/conditional constraints, seed row counts)
  directly in Postgres via the Postgres MCP — or `manage.py dbshell` if the MCP is
  still unavailable, reported as such.

## 13. Documentation

- `docs/module-reference.md`: rows for every new service, selector, view (new
  `### apps/ngo`, `apps/patients`, `apps/psychologists`, `apps/reference`,
  `apps/stats` sections, alphabetical), plus the updated `register_user()` and
  `core/audit.py` rows.
- `docs/architecture.md`: add `reference` and `stats` to the Modules list.
- `docs/decisions.md`: entry for the two new apps and the no-signals orchestration.
- `docs/roadmap.md`: Phase 2 → Done when merged.

## 14. Deployment / data notes

- Not deployed; no production data. Local dev accounts created before this phase
  have no profile and should be recreated (no backfill migration — psychologist/NGO
  credentials can't be invented).
- No new packages. `zoneinfo` is stdlib (Django already pulls `tzdata` on Windows).

## 15. Frontend handoff (not built here)

- Both frontends: new nested `profile` + `is_adult_confirmed` in the register body;
  reference endpoints for dropdowns; `/me/` endpoints per role.
- MindCare App: public/private toggle warning copy (given to the user separately).
- MindCare Web: `VITE_API_BASE_URL` must include `/api/v1`; the placeholder
  `/auth/sign-in`, `/auth/sign-up`, `/therapists` paths don't match backend routes.
