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
| `apps/accounts/services.py` | `register_user()` | Requires the 18+ declaration (stamps `adult_confirmed_at`), creates `User` + role profile in one transaction via `PROFILE_CREATORS` (no signals), logs a `register` audit event only on success | `POST /api/v1/accounts/register/` | MindCare Web, MindCare App |
| `apps/accounts/services.py` | `authenticate_and_check_approval()` | Authenticates credentials and enforces the `approval_status` gate for psychologist/NGO accounts | `POST /api/v1/accounts/login/` | MindCare Web, MindCare App |
| `apps/accounts/services.py` | `record_token_refresh()` | Logs a `token_refresh` audit event | `POST /api/v1/accounts/refresh/` | MindCare Web, MindCare App |
| `apps/accounts/services.py` | `record_logout()` | Logs a `logout` audit event | `POST /api/v1/accounts/logout/` | MindCare Web, MindCare App |
| `apps/accounts/selectors.py` | `get_user_from_refresh_token()` | Decodes a refresh token and looks up its owning user | — | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `RegisterView` | Public registration for patient/psychologist/NGO (never admin); nested role-specific `profile` + `is_adult_confirmed`; returns the user and their profile | `POST /api/v1/accounts/register/` | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `LoginView` | JWT login; embeds `role` claim; blocks pending/rejected accounts; throttled | `POST /api/v1/accounts/login/` | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `RefreshView` | Rotates JWT refresh tokens, blacklists the token just used | `POST /api/v1/accounts/refresh/` | MindCare Web, MindCare App |
| `apps/accounts/api/views.py` | `LogoutView` | Blacklists the presented refresh token | `POST /api/v1/accounts/logout/` | MindCare Web, MindCare App |

---

### apps/ngo

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/ngo/models.py` | `NGOProfile`, `NGOServiceArea` | NGO organisation details (credentials locked; registration number and official contacts admin-only) and service areas (country + optional city; no city = nationwide) | — | MindCare Web |
| `apps/ngo/services.py` | `create_ngo_profile()` | Creates the profile + service areas at registration; validates email, website, phone, timezone and field lengths at the service layer; `official_email` stored normalized (lower-cased); generic duplicate-registration error | via `POST /api/v1/accounts/register/` | MindCare Web |
| `apps/ngo/services.py` | `update_ngo_profile()` | Owner edits; credential lock; service-layer email/website/phone/timezone/length validation; `official_email` stored normalized (lower-cased); a provided `service_areas` list replaces the set | `PATCH /api/v1/ngo/me/` | MindCare Web |
| `apps/ngo/selectors.py` | `get_ngo_profile_for_user()` | Loads the requesting NGO's own profile | `GET /api/v1/ngo/me/` | MindCare Web |
| `apps/ngo/api/views.py` | `MyNGOProfileView` | Owner-only read/update of the NGO profile | `GET`/`PATCH /api/v1/ngo/me/` | MindCare Web |

---

### apps/patients

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/patients/models.py` | `PatientProfile` | Patient demographics/preferences, immutable pseudonym, `is_profile_public` (default False); no health data | — | MindCare App |
| `apps/patients/services.py` | `create_patient_profile()` | Creates the profile at registration with a unique pseudonym (retries collisions) | via `POST /api/v1/accounts/register/` | MindCare App |
| `apps/patients/services.py` | `update_patient_profile()` | Owner edits; rejects pseudonym changes, under-18 DOB, bad timezone/phone; resolves city | `PATCH /api/v1/patients/me/` | MindCare App |
| `apps/patients/selectors.py` | `get_patient_profile_for_user()` | Loads the requesting patient's own profile | `GET /api/v1/patients/me/` | MindCare App |
| `apps/patients/selectors.py` | `get_patient_display_identity()` | Single rule for real name vs pseudonym; an admin reveal of a private profile logs `identity_reveal`; Phases 3/11 must use it | — (no endpoint in Phase 2) | MindCare Web, MindCare App (Phase 3+) |
| `apps/patients/api/views.py` | `MyPatientProfileView` | Owner-only read/update of the patient profile | `GET`/`PATCH /api/v1/patients/me/` | MindCare App |

---

### apps/psychologists

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/psychologists/models.py` | `PsychologistProfile` | Credentials (locked after registration; license number admin-only, unique per issuing country) + editable professional details | — | MindCare Web |
| `apps/psychologists/services.py` | `create_psychologist_profile()` | Creates the profile at registration; normalizes license; generic duplicate-license error | via `POST /api/v1/accounts/register/` | MindCare Web |
| `apps/psychologists/services.py` | `update_psychologist_profile()` | Owner edits; rejects changed credential fields (`credential_field_locked`), accepts unchanged ones; validates `gender` at the service layer (invalid value raises `DomainValidationError`, `None` clears it) | `PATCH /api/v1/psychologists/me/` | MindCare Web |
| `apps/psychologists/selectors.py` | `get_psychologist_profile_for_user()` | Loads the requesting psychologist's own profile | `GET /api/v1/psychologists/me/` | MindCare Web |
| `apps/psychologists/api/views.py` | `MyPsychologistProfileView` | Owner-only read/update of the psychologist profile | `GET`/`PATCH /api/v1/psychologists/me/` | MindCare Web |

---

### apps/reference

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/reference/models.py` | `Country`, `City`, `Language`, `Specialization` | Shared reference data; seeded by migration 0002 (ISO 3166-1, ISO 639-1, major Pakistani cities, PLACEHOLDER specializations), maintained in Django admin | — | MindCare Web, MindCare App |
| `apps/reference/services.py` | `resolve_city()` | Case/whitespace-insensitive city match per country, creating it if new (race-safe) | — (used by profile writes) | MindCare Web, MindCare App |
| `apps/reference/services.py` | `resolve_location_fields()` | Shared country/city rules for profile writes | — | neither (internal) |
| `apps/reference/services.py` | `ensure_active_choices()` | Rejects empty or retired language/specialization choices | — | neither (internal) |
| `apps/reference/selectors.py` | `list_countries()`, `search_cities()`, `list_languages()`, `list_specializations()` | Public dropdown data | see views | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `CountryListView` | List countries | `GET /api/v1/reference/countries/` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `CityListView` | Prefix city search within a country (max 20) | `GET /api/v1/reference/cities/?country=PK&search=lah` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `LanguageListView` | List active languages | `GET /api/v1/reference/languages/` | MindCare Web, MindCare App |
| `apps/reference/api/views.py` | `SpecializationListView` | List active specializations | `GET /api/v1/reference/specializations/` | MindCare Web |

---

### core/ (shared, non-app modules)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `core/permissions.py` | `IsPatient`, `IsPsychologist`, `IsAdmin`, `IsNGO` | Role-level DRF permission classes | — | MindCare Web, MindCare App |
| `core/permissions.py` | `IsOwnerOfObject` | Reusable object-level ownership permission base class, for future apps to subclass | — | (foundation for future apps) |
| `core/audit.py` | `log_auth_event()` | Emits structured, PHI-free JSON audit log lines for auth events | — | neither (internal) |
| `core/exceptions.py` | `DomainValidationError` | Raised by services when a business rule rejects input; views turn it into a 400 | — | neither (internal) |
| `core/validators.py` | `validate_iana_timezone`, `E164_VALIDATOR`, `validate_adult_date_of_birth`, `normalize_display_text`, `normalize_identifier`, `run_validator` | Shared validators/normalizers for profile fields (timezone, phone, 18+ DOB, city names, license/registration numbers) | — | neither (internal) |
| `core/choices.py` | `Gender` | Shared gender choices for patient/psychologist profiles | — | MindCare Web, MindCare App |
| `core/serializers.py` | `RejectUnknownFieldsMixin` | Makes serializers reject undeclared keys (e.g. `pseudonym`) with a 400 | — | neither (internal) |
| `core/audit.py` | `log_identity_reveal()` | Logs `identity_reveal` (viewer id, patient id only) when an admin resolves a private patient's real name | — | neither (internal) |

---

### config/ (project settings)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `config/settings/base.py`, `dev.py`, `prod.py` | `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `corsheaders.middleware.CorsMiddleware` | CORS configured via `django-cors-headers` (`requirements/base.txt`, 4.9.0). `base.py`/`prod.py` allow only the deployed MindCare Web origin (`https://mind-care-web-seven.vercel.app`; pinned explicitly in `prod.py`); `dev.py` adds the Vite dev server (`http://localhost:5173`). `CORS_ALLOW_CREDENTIALS=False` because auth is JWT bearer tokens in the `Authorization` header, not cookies. Middleware sits above `CommonMiddleware` | all `/api/v1/` endpoints | MindCare Web |

<!-- Add new `### apps/<app_name>` sections below as modules are implemented. -->
