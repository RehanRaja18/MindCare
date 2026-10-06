# Module Reference

This is a running technical reference of the backend codebase, built up incrementally
as features are implemented. For every file that carries logic (services, selectors,
API views, tasks, etc.) it records:

- the file and the function/class in it
- what that function/class does
- the API endpoint it powers, if any
- which frontend (MindCare Web, MindCare App, or neither) consumes it

This file is not architecture documentation — see @architecture.md for that. Its
purpose is to give whoever writes the final FYP project documentation a complete,
accurate inventory of the codebase to work from, without having to re-derive it from
the source at the end of the project. It is kept up to date as we go rather than
reconstructed later, per the rule in @../CLAUDE.md.

## How to add an entry

Append a row to the relevant app's table below (add a new `### apps/<app_name>`
section, in alphabetical order, if one doesn't exist yet) whenever you implement a
new service, selector, or API endpoint. Keep entries one row per function/class.

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| _example:_ `apps/accounts/services.py` | `register_patient()` | Creates a `User` + `PatientProfile` in one transaction, sends verification email | `POST /api/v1/accounts/register/` | MindCare Web, MindCare App |

---

### apps/accounts

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/accounts/models.py` | `User` | Custom auth user model: email login, `role`, `approval_status`, `is_super_admin`, `adult_confirmed_at` (18+ declaration timestamp) | — | MindCare Web, MindCare App |
| `apps/accounts/models.py` | `User.last_active_at` | Last activity, psychologists only (shown as a band) | — | MindCare App |
| `apps/accounts/services.py` | `register_user()` | Requires the 18+ declaration (stamps `adult_confirmed_at`), creates `User` + role profile in one transaction via `PROFILE_CREATORS` (no signals), logs a `register` audit event only on success | `POST /api/v1/accounts/register/` | MindCare Web, MindCare App |
| `apps/accounts/services.py` | `authenticate_and_check_approval()` | Authenticates credentials and enforces the `approval_status` gate for psychologist/NGO accounts | `POST /api/v1/accounts/login/` | MindCare Web, MindCare App |
| `apps/accounts/services.py` | `record_token_refresh()` | Logs a `token_refresh` audit event | `POST /api/v1/accounts/refresh/` | MindCare Web, MindCare App |
| `apps/accounts/services.py` | `record_logout()` | Logs a `logout` audit event | `POST /api/v1/accounts/logout/` | MindCare Web, MindCare App |
| `apps/accounts/selectors.py` | `get_user_from_refresh_token()` | Decodes a refresh token and looks up its owning user | — | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `RegisterView` | Public registration for patient/psychologist/NGO (never admin); nested role-specific `profile`; `is_adult_confirmed` must be the JSON boolean `true` (strict, no coercion); returns the user and their profile | `POST /api/v1/accounts/register/` | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `LoginView` | JWT login; embeds `role` claim; blocks pending/rejected accounts; throttled | `POST /api/v1/accounts/login/` | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `RefreshView` | Rotates JWT refresh tokens, blacklists the token just used | `POST /api/v1/accounts/refresh/` | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `LogoutView` | Blacklists the presented refresh token | `POST /api/v1/accounts/logout/` | MindCare Web, MindCare App |
| `apps/accounts/admin.py` | `UserAdmin` | Interim Django-admin approval of pending psychologist/NGO accounts; add disabled (users created only via `register_user()`); password, role, and super-admin flags not editable | `/admin/accounts/user/` | neither (Django admin) |

---

### apps/ngo

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/ngo/models.py` | `NGOProfile`, `NGOServiceArea` | NGO organisation details (credentials locked; registration number and official contacts admin-only) and service areas (country + optional city; no city = nationwide) | — | MindCare Web |
| `apps/ngo/services.py` | `create_ngo_profile()` | Creates the profile + service areas at registration; validates email, website, phone, timezone and field lengths at the service layer; `official_email` stored normalized (lower-cased); generic duplicate-registration error | via `POST /api/v1/accounts/register/` | MindCare Web |
| `apps/ngo/services.py` | `update_ngo_profile()` | Owner edits; credential lock; service-layer email/website/phone/timezone/length validation; `official_email` stored normalized (lower-cased); a provided `service_areas` list replaces the set | `PATCH /api/v1/ngo/me/` | MindCare Web |
| `apps/ngo/selectors.py` | `get_ngo_profile_for_user()` | Loads the requesting NGO's own profile | `GET /api/v1/ngo/me/` | MindCare Web |
| `apps/ngo/admin.py` | `NGOProfileAdmin` | Django-admin corrections; add disabled and `user` read-only (profiles created only by `register_user()`); credential/email edits normalized like the service layer | `/admin/ngo/ngoprofile/` | neither (Django admin) |
| `apps/ngo/api/views.py` | `MyNGOProfileView` | Owner-only read/update of the NGO profile | `GET`/`PATCH /api/v1/ngo/me/` | MindCare Web |

---

### apps/patients

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/patients/models.py` | `PatientProfile` | Patient demographics/preferences, immutable pseudonym, `is_profile_public` (default False); no health data | — | MindCare App |
| `apps/patients/services.py` | `create_patient_profile()` | Creates the profile at registration with a unique pseudonym (retries collisions) | via `POST /api/v1/accounts/register/` | MindCare App |
| `apps/patients/services.py` | `update_patient_profile()` | Owner edits; rejects pseudonym changes, under-18 DOB, bad timezone/phone; resolves city | `PATCH /api/v1/patients/me/` | MindCare App |
| `apps/patients/selectors.py` | `get_patient_profile_for_user()` | Loads the requesting patient's own profile | `GET /api/v1/patients/me/` | MindCare App |
| `apps/patients/selectors.py` | `get_patient_display_identity()` | Single rule for real name vs pseudonym; an admin reveal of a private profile logs `identity_reveal`; the assigned-psychologist exception is now live (accepted relationship to an approved, active psychologist, not logged); Phase 11 must use it | — (no endpoint in Phase 2) | MindCare Web, MindCare App (Phase 3+) |
| `apps/patients/admin.py` | `PatientProfileAdmin` | Django-admin view/edit; add disabled and `user` read-only | `/admin/patients/patientprofile/` | neither (Django admin) |
| `apps/patients/api/views.py` | `MyPatientProfileView` | Owner-only read/update of the patient profile | `GET`/`PATCH /api/v1/patients/me/` | MindCare App |

---

### apps/psychologists

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/psychologists/models.py` | `PsychologistProfile` | Credentials (locked after registration; license number admin-only, unique per issuing country) + editable professional details | — | MindCare Web |
| `apps/psychologists/models.py` | `PsychologistProfile.is_accepting_patients`, `not_accepting_reason` | Psychologist-set "accepting new patients" switch with a reason (`fully_booked`, `away`, `other`) | — | MindCare Web |
| `apps/psychologists/services.py` | `create_psychologist_profile()` | Creates the profile at registration; normalizes license; generic duplicate-license error | via `POST /api/v1/accounts/register/` | MindCare Web |
| `apps/psychologists/services.py` | `update_psychologist_profile()` | Owner edits; rejects changed credential fields (`credential_field_locked`), accepts unchanged ones; validates `gender` at the service layer (invalid value raises `DomainValidationError`, `None` clears it) | `PATCH /api/v1/psychologists/me/` | MindCare Web |
| `apps/psychologists/selectors.py` | `get_psychologist_profile_for_user()` | Loads the requesting psychologist's own profile | `GET /api/v1/psychologists/me/` | MindCare Web |
| `apps/psychologists/admin.py` | `PsychologistProfileAdmin` | Django-admin corrections; add disabled and `user` read-only; license/authority/qualifications edits normalized like the service layer | `/admin/psychologists/psychologistprofile/` | neither (Django admin) |
| `apps/psychologists/api/views.py` | `MyPsychologistProfileView` | Owner-only read/update of the psychologist profile | `GET`/`PATCH /api/v1/psychologists/me/` | MindCare Web |

---

### apps/reference

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/reference/models.py` | `Country`, `City`, `Language`, `Specialization` | Shared reference data; seeded by migration 0002 (ISO 3166-1, ISO 639-1, major Pakistani cities, PLACEHOLDER specializations), maintained in Django admin. `City.is_verified`: seeded cities verified by migration 0003 (which also renames Turkey to Türkiye); cities typed at registration stay unverified until an admin verifies them | — | MindCare Web, MindCare App |
| `apps/reference/services.py` | `resolve_city()` | Case/whitespace-insensitive city match per country, creating it if new (race-safe) | — (used by profile writes) | MindCare Web, MindCare App |
| `apps/reference/services.py` | `resolve_location_fields()` | Shared country/city rules for profile writes | — | neither (internal) |
| `apps/reference/services.py` | `ensure_active_choices()` | Rejects empty or retired language/specialization choices | — | neither (internal) |
| `apps/reference/selectors.py` | `list_countries()`, `search_cities()`, `list_languages()`, `list_specializations()` | Public dropdown data; `search_cities()` returns verified cities only | see views | MindCare Web, MindCare App |
| `apps/reference/admin.py` | `CityAdmin` | Shows/filters/edits `is_verified` inline and offers a "Mark selected cities as verified" action | `/admin/reference/city/` | neither (Django admin) |
| `apps/reference/api/views.py` | `CountryListView` | List countries | `GET /api/v1/reference/countries/` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `CityListView` | Prefix city search within a country (max 20, verified cities only); query validated by `CityQuerySerializer` (`country` required, 2 letters; `search` max 120; null bytes rejected with 400) | `GET /api/v1/reference/cities/?country=PK&search=lah` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `LanguageListView` | List active languages | `GET /api/v1/reference/languages/` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `SpecializationListView` | List active specializations | `GET /api/v1/reference/specializations/` | MindCare Web |

---

### apps/relationships

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/relationships/models.py` | `CareRelationship` | One row per request; becomes the relationship when accepted; one open (pending/accepted) row per patient via `relationships_one_open_per_patient`; profiles referenced with PROTECT | — | MindCare Web, MindCare App |
| `apps/relationships/admin.py` | `CareRelationshipAdmin` | Read-only support view; patients by pseudonym | `/admin/relationships/carerelationship/` | neither (Django admin) |
| `apps/relationships/selectors.py` | `get_active_relationship()` | The single "is this patient in active care?" check (accepted row, psychologist approved and active); Phase 9 hook | — | neither (internal) |
| `apps/relationships/selectors.py` | `is_assigned_psychologist()` | True only for an accepted row to a currently approved, active psychologist; used by `get_patient_display_identity()` | — | neither (internal) |
| `apps/relationships/selectors.py` | `requester_summary()` | Pre-acceptance view of a requester: pseudonym, language, timezone, country, gender, age (never name/city/phone/date of birth) | `GET /api/v1/relationships/inbox/` | MindCare Web |
| `apps/relationships/selectors.py` | `psychologist_inbox()`, `psychologist_patients()`, `psychologist_patient()`, `psychologist_history()`, `patient_current()`, `patient_requests()`, `recent_psychologists()`, `last_active_band()` | Ownership-scoped reads for both sides | see Tasks 7–8 endpoints | MindCare Web, MindCare App |

---

### apps/stats

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/stats/selectors.py` | `get_public_platform_stats()` | Cached (5 min) aggregate counts: active patients (TEMPORARY until Phase 3), approved psychologists, distinct cities of vetted profiles only (active patients; active AND approved psychologists and NGOs; not NGO service areas) | `GET /api/v1/stats/public/` | MindCare Web |
| `apps/stats/api/views.py` | `PublicStatsView` | Unauthenticated, rate-limited (`public_stats`, 60/min) public counts; exact contract `{people_in_care, verified_therapists, cities}` | `GET /api/v1/stats/public/` | MindCare Web |

---

### core/ (shared, non-app modules)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `core/permissions.py` | `IsPatient`, `IsPsychologist`, `IsAdmin`, `IsNGO` | Role-level DRF permission classes | — | MindCare Web, MindCare App |
| `core/permissions.py` | `IsOwnerOfObject` | Reusable object-level ownership permission base class, for future apps to subclass | — | (foundation for future apps) |
| `core/audit.py` | `log_auth_event()` | Emits structured, PHI-free JSON audit log lines for auth events | — | neither (internal) |
| `core/exceptions.py` | `DomainValidationError` | Raised by services when a business rule rejects input; views turn it into a 400 | — | neither (internal) |
| `core/validators.py` | `validate_iana_timezone`, `E164_VALIDATOR`, `validate_adult_date_of_birth`, `normalize_display_text`, `normalize_identifier`, `normalize_email_address`, `run_validator` | Shared validators/normalizers for profile fields (timezone, phone, 18+ DOB, city names, license/registration numbers, email addresses) | — | neither (internal) |
| `core/choices.py` | `Gender` | Shared gender choices for patient/psychologist profiles | — | MindCare Web, MindCare App |
| `core/serializers.py` | `RejectUnknownFieldsMixin` | Makes serializers reject undeclared keys (e.g. `pseudonym`) with a 400; checked in `to_internal_value`, so nested and `many=True` children (e.g. each NGO `service_areas` item) are covered too | — | neither (internal) |
| `core/serializers.py` | `StrictTrueField` | Custom DRF field that accepts **only** the JSON boolean `true`, rejecting coerced truthy values like `"true"`, `1`, `"yes"` (used for legal declarations like the 18+ confirmation); documented as a boolean in the OpenAPI schema | — | neither (internal) |
| `core/audit.py` | `log_identity_reveal()` | Logs `identity_reveal` (viewer id, patient id only) when an admin resolves a private patient's real name | — | neither (internal) |
| `core/audit.py` | `log_relationship_event()` | Relationship state changes (requested/cancelled/accepted/declined/expired/ended) with relationship id, actor id/role and reason only | — | neither (internal) |

---

### config/ (project settings)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `config/settings/base.py`, `dev.py`, `prod.py` | `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `corsheaders.middleware.CorsMiddleware` | CORS configured via `django-cors-headers` (`requirements/base.txt`, 4.9.0). `base.py`/`prod.py` allow only the deployed MindCare Web origin (`https://mind-care-web-seven.vercel.app`; pinned explicitly in `prod.py`); `dev.py` adds the Vite dev server (`http://localhost:5173`). `CORS_ALLOW_CREDENTIALS=False` because auth is JWT bearer tokens in the `Authorization` header, not cookies. Middleware sits above `CommonMiddleware` | all `/api/v1/` endpoints | MindCare Web |

| `manage.py` | `main()` | `manage.py test` forces `config.settings.test` (guarded, local-only DB) so the Django test runner can never run against the `.env` production `DATABASE_URL` | — | neither (tooling) |
| `apps/*/api/views.py` | `extend_schema` annotations | OpenAPI request/response schema for every Phase 2 endpoint (register documents the per-role `profile` shape) | `/api/schema/`, `/api/docs/` | MindCare Web, MindCare App |

---

### config/ (project settings)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `config/settings/base.py`, `dev.py`, `prod.py` | `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `corsheaders.middleware.CorsMiddleware` | CORS configured via `django-cors-headers` (`requirements/base.txt`, 4.9.0). `base.py`/`prod.py` allow only the deployed MindCare Web origin (`https://mind-care-web-seven.vercel.app`; pinned explicitly in `prod.py`); `dev.py` adds the Vite dev server (`http://localhost:5173`). `CORS_ALLOW_CREDENTIALS=False` because auth is JWT bearer tokens in the `Authorization` header, not cookies. Middleware sits above `CommonMiddleware` | all `/api/v1/` endpoints | MindCare Web |

<!-- Add new `### apps/<app_name>` sections below as modules are implemented. -->
