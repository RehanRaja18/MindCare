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
| `apps/accounts/authentication.py` | `ActivityTrackingJWTAuthentication` | DRF default auth: simplejwt + `record_activity()`, except on refresh/logout | all authenticated endpoints | MindCare Web, MindCare App |
| `apps/accounts/schema.py` | `ActivityTrackingJWTScheme` | drf-spectacular extension (registered in `AccountsConfig.ready()`): documents `ActivityTrackingJWTAuthentication` as the `jwtAuth` bearer-JWT security scheme | `/api/docs/`, `/api/schema/` (security on authenticated endpoints) | MindCare Web, MindCare App (API docs) |
| `apps/accounts/admin.py` | `UserAdmin` | Interim Django-admin approval of pending psychologist/NGO accounts; add disabled (users created only via `register_user()`); password, role, and super-admin flags not editable; deactivating/rejecting ends care relationships (moving back to pending only pauses them) | `/admin/accounts/user/` | neither (Django admin) |
| `apps/accounts/demo.py` | `seed_demo_accounts()`, `remove_demo_accounts()`, `DEMO_EMAILS` | Idempotent demo data through the real services: 6 approved psychologists (plain names, bios starting "Demo account, not a real psychologist.", `@example.com`, `DEMO-` licenses; re-running renames accounts seeded with the old "(Demo)" suffix; mixed specializations, languages, cities, genders, accepting on/off) and 2 patients with timezone and date of birth; patient 1 accepted with Dr. Sara Ahmed and patient 2 pending to her (via `request_psychologist()` / `accept_request()`; an expired request is renewed on re-run); removal deletes only those emails, relationship rows first (PROTECT) | — | neither (tooling) |
| `apps/accounts/management/commands/seed_demo.py` | `Command` | `python manage.py seed_demo` (password from the `DEMO_PASSWORD` env var, never printed) and `seed_demo --remove` | — | neither (tooling) |

---

### apps/ai

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `integrations/ai_service/client.py` | `predict()`, `AIServiceUnavailable`, `AIServiceRejected` | Stdlib HTTP call to the AI service's `POST /predict` (base URL from `AI_SERVICE_URL`); 400/422 → rejected with the AI's flattened `detail`; timeout, connection error, 5xx, other 4xx, non-JSON or no URL → unavailable; never logs the body | — | neither (internal) |
| `apps/ai/services.py` | `predict_anxiety_risk()` | Forwards the features with a 60 s timeout; nothing stored or logged (health data, no audit trail before Phase 5) | `POST /api/v1/ai/anxiety-prediction/` | MindCare Web |
| `apps/ai/api/serializers.py` | `AnxietyPredictionRequestSerializer`, `AnxietyPredictionResponseSerializer`, `OCCUPATIONS` | Request keys exactly as the AI expects (17 fields, same bounds as its schema, unknown keys rejected); response documents the AI's shape | — | MindCare Web |
| `apps/ai/api/views.py` | `AnxietyPredictionView`, `AIPredictionRateThrottle` | Approved, active psychologists only (patients 403); AI rejection → 400 `{detail}`; AI unavailable → 503 "waking up"; throttled (`ai_prediction`, 20/min per user) | `POST /api/v1/ai/anxiety-prediction/` | MindCare Web |

---

### apps/motivation

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/motivation/models.py` | `MotivationalContent`, `Quote`, `QuoteCategory` | Abstract base (`is_active`, `created_at`) for Motivation Corner content; `Quote` = text, optional author, optional category (`hope`, `resilience`, `calm`, `self_care`). Religious content (Dua/Surah/Hadith with audio) will be a separate model, served only on opt-in. Migration 0002 seeds 30 non-religious quotes | — | MindCare App |
| `apps/motivation/selectors.py` | `active_quotes()`, `random_active_quote()` | Active quotes only, newest first, optional category; random pick by count + random offset (no `ORDER BY RANDOM()`), `None` when there are none | see views | MindCare App |
| `apps/motivation/admin.py` | `QuoteAdmin` | List, search (text, author), filter, inline `is_active` toggle and show/hide actions; changes appear in the API on the next request | `/admin/motivation/quote/` | neither (Django admin) |
| `apps/motivation/api/serializers.py` | `QuoteSerializer`, `QuoteQuerySerializer` | `{id, text, author, category}`, blank author/category as `null`; `category` query param validated (unknown → 400) | — | MindCare App |
| `apps/motivation/api/views.py` | `QuoteListView`, `RandomQuoteView`, `MotivationRateThrottle` | Any logged-in user; paginated active quotes with `?category=`, and one random active quote (404 `No quotes available.`); throttled (`motivation`, 60/min per user, shared by both) | `GET /api/v1/motivation/quotes/`, `GET /api/v1/motivation/quotes/random/` | MindCare App |

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
| `apps/patients/services.py` | `update_patient_profile()` | Owner edits; rejects pseudonym changes, under-18 DOB, bad timezone/phone; resolves city; date of birth can be corrected but never cleared once set (Phase 3) | `PATCH /api/v1/patients/me/` | MindCare App |
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
| `apps/psychologists/selectors.py` | `visible_psychologists()`, `list_directory()`, `get_directory_entry()` | Approved, active psychologists only; filters (specialization, language, gender, country, city, accepting, name search) combined with AND; accepting first, then most recently active (never active last), then name | `GET /api/v1/psychologists/directory/` | MindCare App |
| `apps/psychologists/admin.py` | `PsychologistProfileAdmin` | Django-admin corrections; add disabled and `user` read-only; license/authority/qualifications edits normalized like the service layer | `/admin/psychologists/psychologistprofile/` | neither (Django admin) |
| `apps/psychologists/api/views.py` | `MyPsychologistProfileView` | Owner-only read/update of the psychologist profile | `GET`/`PATCH /api/v1/psychologists/me/` | MindCare Web |
| `apps/psychologists/api/serializers.py` | `DIRECTORY_CARD_FIELDS`, `DirectoryCardSerializer`, `MinimalCardSerializer`, `DirectoryQuerySerializer` | Patient-facing psychologist card with an explicit field list (never `license_number`, `last_active_at`, `not_accepting_reason`); `last_active` as a band; minimal `{id, full_name}` card when the psychologist is no longer approved and active; directory query params validated (bad `city`/`accepting`/`gender` give 400; whitespace-only `search` means no filter) | `GET /api/v1/psychologists/directory/` | MindCare App |
| `apps/psychologists/api/views.py` | `DirectoryListView`, `DirectoryDetailView`, `DirectoryRateThrottle` | Logged-in patients only; paginated directory (20 per page, max 50) and single card (404 if not approved and active); throttled (`directory`, 60/min) | `GET /api/v1/psychologists/directory/`, `GET /api/v1/psychologists/directory/<id>/` | MindCare App |
| `apps/psychologists/api/serializers.py` | `BlankAsNoneChoiceField` | `ChoiceField` where `""`, whitespace-only and `null` all mean "no reason given" (`None`), so the service returns its single "Choose a reason…" message instead of DRF's "not a valid choice"; used for the availability `reason` and the psychologist end `reason` | `PUT /api/v1/psychologists/me/availability/`, `POST /api/v1/relationships/patients/<id>/end/` | MindCare Web |
| `apps/psychologists/api/serializers.py` | `AvailabilitySerializer` | Availability body `{accepting, reason}`; `reason` from `NotAcceptingReason`, unknown keys rejected | `PUT /api/v1/psychologists/me/availability/` | MindCare Web |
| `apps/psychologists/api/views.py` | `AvailabilityView` | The psychologist's own "accepting new patients" switch; approved, active psychologists only (403 when pending/rejected/inactive); reason required when off (400), cleared when on; the reason is never shown to patients | `GET`/`PUT /api/v1/psychologists/me/availability/` | MindCare Web |

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
| `apps/relationships/models.py` | `CareRelationship.effective_status` | Read-only status with expiry evaluated on read (a pending row past `expires_at` reads as `expired`); never writes, services persist the expiry on their next write; the `status` shown in the patient view | — | MindCare Web, MindCare App |
| `apps/relationships/admin.py` | `CareRelationshipAdmin` | Read-only support view; patients by pseudonym | `/admin/relationships/carerelationship/` | neither (Django admin) |
| `apps/relationships/selectors.py` | `get_active_relationship()` | The single "is this patient in active care?" check (accepted row, psychologist approved and active); Phase 9 hook | — | neither (internal) |
| `apps/relationships/selectors.py` | `is_assigned_psychologist()` | True only for an accepted row to a currently approved, active psychologist; used by `get_patient_display_identity()` | — | neither (internal) |
| `apps/relationships/selectors.py` | `requester_summary()` | Pre-acceptance view of a requester: pseudonym, language, timezone, country, gender, age (never name/city/phone/date of birth) | `GET /api/v1/relationships/inbox/` | MindCare Web |
| `apps/relationships/selectors.py` | `psychologist_inbox()`, `psychologist_patients()`, `psychologist_patient()`, `psychologist_history()`, `patient_current()`, `patient_requests()`, `recent_psychologists()`, `last_active_band()` | Ownership-scoped reads for both sides; psychologist reads cover only the caller's own rows | `GET /api/v1/relationships/{inbox,patients,patients/<id>,history,current,requests,recent}/` | MindCare Web, MindCare App |
| `apps/relationships/selectors.py` | `psychologist_is_visible()` | Shared "approved and active" check for a psychologist profile (used by the selectors above and the patient-view serializer's full vs minimal card) | — | neither (internal) |
| `apps/relationships/services.py` | `request_psychologist()` | Date of birth required; generic "isn't available" for unapproved/inactive/unknown psychologists; accepting check; stale pending expired in the same transaction; one open row; 30-day decline cooldown | `POST /api/v1/relationships/requests/` | MindCare App |
| `apps/relationships/services.py` | `cancel_request()`, `accept_request()`, `decline_request()` | Row-locked, ownership-checked (404), expiry-aware state changes; decline sets the 30-day cooldown | `POST /api/v1/relationships/requests/<id>/{cancel,accept,decline}/` | MindCare App, MindCare Web |
| `apps/relationships/services.py` | `end_relationship()` | The only way an accepted relationship ends; reason validated per `ended_by` (`subscription_lapsed` system-only, reserved for Phase 9); row-locked; "ended" audit line written only after commit | — (called by the views below and by Phase 9) | neither (internal) |
| `apps/relationships/services.py` | `patient_end_relationship()` | Patient ends their psychologist; `confirm` must be JSON `true` | `POST /api/v1/relationships/current/end/` | MindCare App |
| `apps/relationships/services.py` | `psychologist_end_relationship()` | Psychologist ends with a required reason (`treatment_completed`, `referred_elsewhere`, `other`) | `POST /api/v1/relationships/patients/<id>/end/` | MindCare Web |
| `apps/relationships/services.py` | `end_for_unavailable_account()` | On deactivation or rejection: accepted rows end (system/account_unavailable), pending rows expire; not on pending (pause) | — (called from `UserAdmin.save_model`) | neither (internal) |
| `apps/relationships/services.py` | `set_accepting_status()` | Accepting switch; reason required when off, cleared when on | `PUT /api/v1/psychologists/me/availability/` | MindCare Web |
| `apps/relationships/services.py` | `record_activity()` | Psychologist `last_active_at`, at most every 15 min via cache key; cache errors skip silently; a failed DB write clears the key and logs one warning with the exception type only (no user id, message or traceback) | — | neither (internal) |
| `apps/relationships/api/serializers.py` | `RequestCreateSerializer`, `PatientEndSerializer`, `RelationshipPatientViewSerializer` | Request body (`psychologist` id, unknown keys rejected); end confirmation via `StrictTrueField`; the patient's view of a relationship with the full card or the minimal card | — | MindCare App |
| `apps/relationships/api/views.py` | `RequestListCreateView`, `RelationshipRequestRateThrottle` | GET: the patient's paginated request history (the App's history screen); POST: send a request (only POST throttled, `relationship_requests`, 10/hour) | `GET`/`POST /api/v1/relationships/requests/` | MindCare App |
| `apps/relationships/api/views.py` | `CancelRequestView` | Patient cancels their own pending request (another patient's gives 404) | `POST /api/v1/relationships/requests/<id>/cancel/` | MindCare App |
| `apps/relationships/api/views.py` | `CurrentRelationshipView` | The patient's pending (unexpired) or accepted relationship, or `{"relationship": null}` | `GET /api/v1/relationships/current/` | MindCare App |
| `apps/relationships/api/views.py` | `EndCurrentRelationshipView` | Patient ends their psychologist; body `{"confirm": true}` (JSON true only) | `POST /api/v1/relationships/current/end/` | MindCare App |
| `apps/relationships/api/views.py` | `RecentPsychologistsView` | Up to 10 past psychologists (approved, active, no open row) as directory cards | `GET /api/v1/relationships/recent/` | MindCare App |
| `apps/relationships/api/serializers.py` | `InboxItemSerializer`, `AssignedPatientSerializer`, `ASSIGNED_PATIENT_FIELDS`, `HistoryItemSerializer`, `DeclineSerializer`, `PsychologistEndSerializer` | Psychologist-facing shapes: inbox item with `requester_summary()` (pseudonym, language, timezone, country, gender, age; no name); assigned patient (real name, age, never `date_of_birth`); history item (pseudonym only); decline body (optional `reason`) and end body (`reason` from `treatment_completed`/`referred_elsewhere`/`other`), unknown keys rejected | — | MindCare Web |
| `apps/relationships/api/views.py` | `InboxView` | The psychologist's own pending, unexpired requests, oldest first; logged-in, approved and active psychologists only (`IsPsychologist` + `IsApprovedPsychologist`) | `GET /api/v1/relationships/inbox/` | MindCare Web |
| `apps/relationships/api/views.py` | `AcceptRequestView` | Accept an own pending request → `{id, status}`; another psychologist's request gives 404, a stale one 400; logged-in, approved and active psychologists only (`IsPsychologist` + `IsApprovedPsychologist`) | `POST /api/v1/relationships/requests/<id>/accept/` | MindCare Web |
| `apps/relationships/api/views.py` | `DeclineRequestView` | Decline an own pending request with an optional reason (starts the 30-day cooldown) → `{id, status}`; another psychologist's gives 404; logged-in, approved and active psychologists only (`IsPsychologist` + `IsApprovedPsychologist`) | `POST /api/v1/relationships/requests/<id>/decline/` | MindCare Web |
| `apps/relationships/api/views.py` | `PatientListView` | The psychologist's current (accepted) patients with real name and age, never date of birth; logged-in, approved and active psychologists only (`IsPsychologist` + `IsApprovedPsychologist`) | `GET /api/v1/relationships/patients/` | MindCare Web |
| `apps/relationships/api/views.py` | `PatientDetailView` | One current patient; 404 unless it is the caller's own accepted row (access ends the moment care ends); logged-in, approved and active psychologists only (`IsPsychologist` + `IsApprovedPsychologist`) | `GET /api/v1/relationships/patients/<id>/` | MindCare Web |
| `apps/relationships/api/views.py` | `PatientEndView` | Psychologist ends an own relationship; `reason` required (`Choose a reason.`), `patient_unresponsive` rejected; returns the history item; another psychologist's row gives 404; logged-in, approved and active psychologists only (`IsPsychologist` + `IsApprovedPsychologist`) | `POST /api/v1/relationships/patients/<id>/end/` | MindCare Web |
| `apps/relationships/api/views.py` | `HistoryView` | The psychologist's own ended relationships, pseudonym only (not the patient's request history, which is `GET /requests/`); logged-in, approved and active psychologists only (`IsPsychologist` + `IsApprovedPsychologist`) | `GET /api/v1/relationships/history/` | MindCare Web |

---

### apps/stats

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `apps/stats/selectors.py` | `get_public_platform_stats()` | Cached (5 min) aggregate counts: `people_in_care` = patients with an accepted relationship to an approved, active psychologist (Phase 3; no longer temporary), approved psychologists, distinct cities of vetted profiles only (active patients; active AND approved psychologists and NGOs; not NGO service areas) | `GET /api/v1/stats/public/` | MindCare Web |
| `apps/stats/api/views.py` | `PublicStatsView` | Unauthenticated, rate-limited (`public_stats`, 60/min) public counts; exact contract `{people_in_care, verified_therapists, cities}` | `GET /api/v1/stats/public/` | MindCare Web |

---

### core/ (shared, non-app modules)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `core/permissions.py` | `IsPatient`, `IsPsychologist`, `IsAdmin`, `IsNGO` | Role-level DRF permission classes | — | MindCare Web, MindCare App |
| `core/permissions.py` | `IsApprovedPsychologist` | Psychologist whose account is active and approved (pending/paused, rejected and deactivated are refused); used with `IsPsychologist` on every Phase 3 psychologist endpoint, not on the Phase 2 `/me/` profile endpoints | all psychologist-facing `/api/v1/relationships/` endpoints, `/api/v1/psychologists/me/availability/` | MindCare Web |
| `core/permissions.py` | `IsOwnerOfObject` | Reusable object-level ownership permission base class, for future apps to subclass | — | (foundation for future apps) |
| `core/audit.py` | `log_auth_event()` | Emits structured, PHI-free JSON audit log lines for auth events | — | neither (internal) |
| `core/exceptions.py` | `DomainValidationError` | Raised by services when a business rule rejects input; views turn it into a 400 | — | neither (internal) |
| `core/validators.py` | `validate_iana_timezone`, `E164_VALIDATOR`, `validate_adult_date_of_birth`, `normalize_display_text`, `normalize_identifier`, `normalize_email_address`, `run_validator` | Shared validators/normalizers for profile fields (timezone, phone, 18+ DOB, city names, license/registration numbers, email addresses) | — | neither (internal) |
| `core/choices.py` | `Gender` | Shared gender choices for patient/psychologist profiles | — | MindCare Web, MindCare App |
| `core/serializers.py` | `RejectUnknownFieldsMixin` | Makes serializers reject undeclared keys (e.g. `pseudonym`) with a 400; checked in `to_internal_value`, so nested and `many=True` children (e.g. each NGO `service_areas` item) are covered too | — | neither (internal) |
| `core/serializers.py` | `StrictTrueField` | Custom DRF field that accepts **only** the JSON boolean `true`, rejecting coerced truthy values like `"true"`, `1`, `"yes"` (used for legal declarations like the 18+ confirmation); documented as a boolean in the OpenAPI schema | — | neither (internal) |
| `core/pagination.py` | `StandardPagination` | Shared page-number pagination: 20 per page by default, `page_size` query param capped at 50 | all paginated list endpoints | MindCare Web, MindCare App |
| `core/audit.py` | `log_identity_reveal()` | Logs `identity_reveal` (viewer id, patient id only) when an admin resolves a private patient's real name | — | neither (internal) |
| `core/audit.py` | `log_relationship_event()` | Relationship state changes (requested/cancelled/accepted/declined/expired/ended) with relationship id, actor id/role and reason only | — | neither (internal) |

---

### config/ (project settings)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `config/settings/base.py`, `dev.py`, `prod.py` | `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `corsheaders.middleware.CorsMiddleware` | CORS configured via `django-cors-headers` (`requirements/base.txt`, 4.9.0). `base.py`/`prod.py` allow the deployed MindCare Web origin (`https://mind-care-web-seven.vercel.app`; pinned explicitly in `prod.py`) plus any origins in the `CORS_EXTRA_ALLOWED_ORIGINS` env var (comma-separated, unset by default); `dev.py` adds the Vite dev server (`http://localhost:5173`) and the Flutter web dev server (`http://localhost:5000`). `CORS_ALLOW_CREDENTIALS=False` because auth is JWT bearer tokens in the `Authorization` header, not cookies. Middleware sits above `CommonMiddleware` | all `/api/v1/` endpoints | MindCare Web |
| `config/settings/prod.py` | `SECURE_HSTS_SECONDS` | HSTS at 86400 s (one day) to start, no `includeSubDomains`; to be raised to one year after a quiet week | all responses | MindCare Web, MindCare App |
| `manage.py` | `main()` | `manage.py test` forces `config.settings.test` (guarded, local-only DB) so the Django test runner can never run against the `.env` production `DATABASE_URL` | — | neither (tooling) |
| `apps/*/api/views.py` | `extend_schema` annotations | OpenAPI request/response schema for every Phase 2 and Phase 3 endpoint (register documents the per-role `profile` shape) | `/api/schema/`, `/api/docs/` | MindCare Web, MindCare App |

### core (input validation)

| File | Function / Class | Purpose | API Endpoint | Frontend Consumer |
|------|-------------------|---------|--------------|--------------------|
| `core/validators.py` | `PersonNameValidator`, `OrganisationNameValidator`, `FreeTextValidator`, `IdentifierValidator`, `HttpsUrlValidator`, `validate_phone`, `validate_adult_date_of_birth`, `normalize_single_line()`, `normalize_multiline_text()`, `normalize_phone()`, `normalize_identifier()`, `normalize_email_address()` | The input rules and exact messages of docs/validation-rules.md; class validators are `@deconstructible` so they sit on model fields | all write endpoints | MindCare Web, MindCare App (they mirror the rules) |
| `core/fields.py` | `PersonNameField`, `OrganisationNameField`, `FreeTextField`, `IdentifierField`, `PhoneField`, `HttpsUrlField` | Model fields that normalise in `to_python()` and carry the matching validator, so Django admin forms and `full_clean()` apply the rules | all write endpoints, Django admin | neither (internal) |
| `core/models.py` | `ValidatedModelMixin` | `save()` runs the field rules (relations, uniqueness and constraints left to the database); `save(update_fields=…)` validates only those fields; failures raise `DomainValidationError` (400). Used by `User`, the three profiles, reference tables and `Quote` | all write endpoints, management commands | neither (internal) |
| `core/serializers.py` | `NormalizedCharField`, `person_name_field()`, `organisation_name_field()`, `free_text_field()`, `identifier_field()`, `phone_field()`, `https_url_field()`, `search_field()`, `whole_number_field()`, `number_field()` | DRF fields that normalise and validate exactly like the model fields, so errors come back under the request's own key | register, `/me/` profiles, directory search, AI form | MindCare Web, MindCare App |

<!-- Add new `### apps/<app_name>` sections below as modules are implemented. -->
