# Design: Phase 3 — Psychologist ↔ Patient Relationships

**Date:** 2026-10-05 (decisions finalised 2026-10-06)
**Status:** Draft — awaiting user review
**Branch:** `phase-3-relationships`
**Apps:** new `apps/relationships`; changes to `apps/psychologists`, `apps/patients`,
`apps/accounts`, `apps/stats`, `core/audit.py`, `config/`.

Every rule here was settled in the Phase 3 requirements interview. The reasoning is
recorded in @../../decisions.md (entries dated 2026-10-06). Where this spec and
`decisions.md` ever disagree, stop and ask.

## 1. Purpose

Let a patient find a psychologist, send one request, and, once the psychologist
accepts, have exactly one active psychologist. That psychologist then sees the
patient's real identity and full profile (except the exact date of birth) for as
long as the relationship lasts. Phases 4–6 (appointments, notes, AI
recommendations) and Phase 9 (subscriptions) build on this relationship.

## 2. Scope

**In scope**
- `CareRelationship` model and its lifecycle (request, accept, decline, cancel,
  expire, end), in a new `apps/relationships` app.
- Psychologist directory for logged-in patients; recent psychologists list.
- Psychologist inbox, current patients, history; "accepting new patients" switch.
- Requiring a date of birth at request time; never clearable once set.
- Wiring the assigned-psychologist exception into `get_patient_display_identity()`.
- Psychologist activity ("last active") tracking, shown as bands.
- Ending relationships automatically when an account is deactivated or rejected.
- Switching `/stats/public/` `people_in_care` to accepted relationships.
- Relationship audit log events; read-only Django admin.

**Explicitly not built (owner in parentheses)**
- Any free-text note from the patient or the psychologist (deferred; rules for any
  future note recorded in decisions.md).
- Emails and reminders: new-request email, reminder 3–5 hours before expiry,
  patient notified when a psychologist ends (Phase 10; scheduler Phase 7).
- Subscriptions, payments, refunds, ending on lapse (Phase 9). Relationships are
  **free until Phase 9**.
- Misconduct reports in both directions (moderation app + Phase 2.5 admin tools;
  scheduled after Phase 3).
- What the patient sees while their psychologist is paused for re-review
  (Phase 2.5).
- Automatic "fully booked" capacity cap; several psychologists per patient;
  sorting the directory by years of experience; background expiry sweep.
- No new third-party packages.

## 3. Lifecycle and statuses

One `CareRelationship` row per request; the row becomes the relationship once
accepted. A returning patient creates a new row each time.

```
pending ──accept──► accepted ──end──► ended
   │
   ├──decline──► declined
   ├──cancel───► cancelled   (by the patient)
   └──expiry───► expired     (3 days unanswered, or account unavailable)
```

No other transitions; no row is ever reopened.

- **Expiry is evaluated on read.** A `pending` row whose `expires_at` has passed is
  treated as expired by every selector and service. Services that touch such a row
  set its status to `expired` (and log the event). There is no background job.
- **Before creating a request,** the patient's stale pending row is marked expired
  inside the same transaction, so the one-open-row constraint doesn't block them.
- **A relationship lasts until someone ends it.** Nothing ends on its own until
  Phase 9 adds subscription lapse.
- **Pause, not end, for a psychologist under re-review.** If a psychologist's
  `approval_status` becomes `pending` (a future Phase 2.5 re-review), their accepted
  relationships stay `accepted`. Care is effectively paused: they can't log in, and
  every selector already requires the psychologist to be approved and active, so
  they get no access, the patient isn't counted in `people_in_care`, and the
  patient's views show a minimal card. The patient can still end the relationship.
  Phase 2.5 decides what the patient is told during a pause.
- **Automatic ending happens only when an account is deactivated
  (`is_active=False`) or rejected (`approval_status="rejected"`).**

## 4. Limits and numbers

| Rule | Value |
|------|-------|
| Request expiry | **3 days**: `expires_at = requested_at + 72h` |
| Re-request cooldown after a **decline** (that psychologist only) | **30 days**: `cooldown_until = responded_at + 30d` |
| Cooldown after cancel, expiry, or a psychologist ending | **none** (a psychologist who doesn't want a patient back can decline the next request, which starts the cooldown) |
| Open rows per patient (pending or accepted) | **1** |
| Activity write frequency per psychologist | at most once per **15 minutes** |
| Recent psychologists list | at most **10** |
| Directory page size | default **20**, maximum **50** (`page_size` query param) |
| Last-active bands | `today` (< 24 h), `this_week` (< 7 days), `this_month` (< 30 days), `over_a_month`, `never` (null) |
| Age | whole years from `date_of_birth`, computed live on the server's local date |

## 5. Data model and constraints

### 5.1 `apps/relationships/models.py` — `CareRelationship`

| Field | Type | Notes |
|-------|------|-------|
| `patient` | FK → `patients.PatientProfile`, `on_delete=PROTECT`, `related_name="care_relationships"` | |
| `psychologist` | FK → `psychologists.PsychologistProfile`, `on_delete=PROTECT`, `related_name="care_relationships"` | |
| `status` | CharField, `RelationshipStatus` | `pending`, `accepted`, `declined`, `cancelled`, `expired`, `ended` |
| `requested_at` | DateTimeField, default now | |
| `expires_at` | DateTimeField | `requested_at + 3 days`; stored for Phase 10's reminder |
| `responded_at` | DateTimeField, null | set on accept or decline |
| `decline_reason` | CharField, `DeclineReason`, null | optional on decline |
| `cooldown_until` | DateTimeField, null | `responded_at + 30 days`, set on decline only |
| `ended_at` | DateTimeField, null | |
| `ended_by` | CharField, `EndedBy`, null | `patient`, `psychologist`, `system` |
| `end_reason` | CharField, `EndReason`, null | |
| `created_at` / `updated_at` | auto | |

**There is no `decline_note` or any free-text field.**

Constraints and indexes:
- `UniqueConstraint(fields=["patient"], condition=Q(status__in=["pending", "accepted"]), name="relationships_one_open_per_patient")`.
- `Index(fields=["psychologist", "status"])`.
- No database check constraints on field consistency; services enforce it.

**`PROTECT` consequence (documented in the admin docstring and in
`docs/deployment.md`):** a user whose profile has relationship rows can't be deleted
from Django admin. Test accounts must have their relationship rows deleted first.

### 5.2 Fixed reason lists (code, not admin-editable)

| List | Codes (display text) |
|------|----------------------|
| `DeclineReason` | `outside_specializations` (Outside my specializations), `language_or_timezone_mismatch` (Language or time-zone mismatch), `case_type_not_taken` (Not taking this type of case), `other` (Other) |
| `EndReason`, psychologist | `treatment_completed` (Treatment completed), `referred_elsewhere` (Referred to another professional), `other` (Other) |
| `EndReason`, patient | `patient_ended` (Ended by the patient) |
| `EndReason`, system | `account_unavailable` (Account unavailable), `subscription_lapsed` (Subscription lapsed — **reserved for Phase 9, unused in Phase 3**) |
| `EndedBy` | `patient`, `psychologist`, `system` |
| `NotAcceptingReason` (on `PsychologistProfile`) | `fully_booked` (Fully booked), `away` (Away / on leave), `other` (Other) |

`patient_unresponsive` is **not** an end reason (removed during the interview).

### 5.3 Changes to existing models

- `PsychologistProfile`: `is_accepting_patients` (BooleanField, default `True`),
  `not_accepting_reason` (CharField, `NotAcceptingReason`, null). Additive migration.
- `User`: `last_active_at` (DateTimeField, null). Written only for psychologists.
  Existing psychologists stay `null` ("never": not seen since tracking began).
- `PatientProfile`: **no change.** `date_of_birth` stays where it is; Phase 3 only
  changes the update rule (§6.9).

### 5.4 Phase 9 hooks (integrate without breaking anything)

- Phase 9 adds `Subscription → CareRelationship` (a new table; additive migration;
  existing rows untouched).
- Lapse calls `end_relationship(rel, ended_by="system", reason="subscription_lapsed")`;
  the reason code already exists.
- "Is this patient in active care?" is answered only by
  `relationships.selectors.get_active_relationship(patient)`; Phase 9 adds "and the
  subscription is paid" there, and every caller inherits it.

## 6. Services and rules (`apps/relationships/services.py`)

All writes run in `transaction.atomic()`. **`accept`, `decline`, `cancel` and every
`end` take the row with `select_for_update()` and re-read its status under the
lock**, so concurrent actions (accept vs cancel; patient-end vs psychologist-end)
can't both succeed.

**6.1 `request_psychologist(*, patient_user, psychologist_id)`**, in order:
1. The patient's profile has a `date_of_birth`, else 400 `date_of_birth`.
2. The psychologist exists **and** is approved **and** active, else the generic 400
   `psychologist` "isn't available" (same response for pending, rejected,
   deactivated and nonexistent; reveals nothing).
3. The psychologist `is_accepting_patients`, else 400 "isn't accepting".
4. Mark the patient's stale pending row (if any) `expired`.
5. No open row (pending or accepted) exists, else 400 `relationship`.
6. No decline by this psychologist with `cooldown_until` in the future, else 400
   with the date.
7. Create the `pending` row with `expires_at`. A unique-constraint `IntegrityError`
   from a simultaneous request becomes the 400 `relationship` error.

**6.2 `cancel_request(*, patient_user, relationship_id)`** — the patient's own row
(else 404), `pending` and not expired (else 400 "no longer pending") → `cancelled`.

**6.3 `accept_request(*, psychologist_user, relationship_id)`** — the psychologist's
own row (else 404); the psychologist is currently approved and active (else 404);
`pending` and not expired (else 400) → `accepted`, `responded_at=now`. Allowed even
when `is_accepting_patients` is off (existing requests can still be answered).

**6.4 `decline_request(*, psychologist_user, relationship_id, reason=None)`** — same
ownership and state checks → `declined`, `responded_at`, `cooldown_until`,
optional `decline_reason`.

**6.5 `end_relationship(*, relationship, ended_by, reason)`** — **the only way an
accepted relationship ends.** Requires `accepted` (re-read under lock, else 400).
Validates the reason against `ended_by`: psychologist reasons for `psychologist`,
`patient_ended` for `patient`, `account_unavailable` / `subscription_lapsed` for
`system`. Sets `ended`, `ended_at`, `ended_by`, `end_reason`.

**6.6 Wrappers:** `patient_end_relationship(*, patient_user, confirm)` (the patient's
accepted row, else 400 "You don't have a psychologist right now"; `confirm` must be
JSON `true`) and `psychologist_end_relationship(*, psychologist_user,
relationship_id, reason)` (own accepted row with that psychologist approved and
active, else 404; reason required).

**6.7 `end_for_unavailable_account(*, user)`** — runs only when a user is
**deactivated** or **rejected**. Inside one transaction with `select_for_update()`:
accepted rows involving the user → `end_relationship(…, "system",
"account_unavailable")`; pending rows → `expired`. Not called when a psychologist
becomes `pending` (that is a pause, §3).

**6.8 `set_accepting_status(*, psychologist_user, accepting, reason=None)`** — a
reason is required when `accepting=False`; cleared when `accepting=True`. Pending
requests are unaffected.

**6.9 Date of birth rule** (in `patients.services.update_patient_profile`): if a
`date_of_birth` is already set, a request to set it to `null`/empty → 400
`{"date_of_birth": ["Your date of birth can't be removed once set."]}`. Correcting it
to another valid 18+ date still works. A patient who never set one is unaffected.
Phase 2's `test_dob_can_be_cleared` is replaced by tests for this rule.
Pre-acceptance age is computed live, so a correction after requesting changes the
age shown (accepted: date of birth is self-reported).

**6.10 `record_activity(*, user)`** — returns immediately unless
`user.role == psychologist`. Then: if the cache key `last_active:<user_id>` exists,
do nothing; otherwise one `User.objects.filter(pk=…).update(last_active_at=now)` and
set the key for 15 minutes. **Any cache error is caught and skips the update; it
never breaks authentication.**

## 7. Selectors

**`apps/relationships/selectors.py`**
- `get_active_relationship(*, patient)` — the patient's `accepted` row whose
  psychologist is approved and active, else `None`. Phase 9 hook.
- `is_assigned_psychologist(*, viewer, patient_profile)` — true only if `viewer` is
  a psychologist, currently approved and active, with an `accepted` row with this
  patient. Wired into `patients.selectors.get_patient_display_identity()` in place
  of the Phase 2 stub (still unlogged).
- `requester_summary(*, relationship)` → exactly `{pseudonym, preferred_language,
  timezone, country, gender, age}`.
- `psychologist_inbox(*, psychologist_user)` — own `pending`, not expired, oldest
  first.
- `psychologist_patients(*, psychologist_user)` / `psychologist_patient(…, relationship_id)`
  — own `accepted` rows, only while the psychologist is approved and active.
- `psychologist_history(*, psychologist_user)` — own `ended` rows; pseudonym only.
- `patient_current(*, patient_user)` — the patient's open row (pending not expired,
  or accepted), else `None`.
- `patient_requests(*, patient_user)` — all the patient's rows, newest first.
- `recent_psychologists(*, patient_user)` — distinct psychologists from the patient's
  `ended` rows, most recent first, at most 10, excluding any current or pending
  psychologist, only those approved and active.
- `last_active_band(dt)` → one of the five band codes.

**`apps/psychologists/selectors.py`**
- `list_directory(*, specialization, language, gender, country, city, accepting,
  search)` — approved, active psychologists only; filters combine with AND, each
  takes one value; `search` = case-insensitive name contains; ordered
  `is_accepting_patients` desc, then `last_active_at` desc nulls last, then name.
- `get_directory_entry(*, profile_id)` — same visibility rule, else `None` (→ 404).

**`apps/stats/selectors.py`** — `people_in_care` = active patients with an `accepted`
relationship to an approved, active psychologist. The "temporary" comment is removed.

## 8. Endpoints

All require login, are limited by role, and are documented with `@extend_schema`.
Another user's row → **404**. Rule violations → 400 in the standard field-error
format. The `relationships` app is mounted at `/api/v1/relationships/`.

**Patient (`IsAuthenticated` + `IsPatient`)**

| Method + path | Does |
|---------------|------|
| `GET /api/v1/psychologists/directory/` | Paginated cards. Query: `specialization` (slug), `language` (ISO code), `gender`, `country` (ISO code), `city` (city id), `accepting` (`true`/`false`), `search`, `page`, `page_size` |
| `GET /api/v1/psychologists/directory/<id>/` | One card; 404 unless approved and active |
| `POST /api/v1/relationships/requests/` | Body `{"psychologist": <profile id>}` → 201, relationship (patient view) |
| `POST /api/v1/relationships/requests/<id>/cancel/` | → 200, relationship (patient view) |
| `GET /api/v1/relationships/requests/` | The patient's request history (paginated) |
| `GET /api/v1/relationships/current/` | `{"relationship": <patient view>}` or `{"relationship": null}` (200) |
| `POST /api/v1/relationships/current/end/` | Body `{"confirm": true}` (`StrictTrueField`) → 200 |
| `GET /api/v1/relationships/recent/` | Up to 10 cards |

**Psychologist (`IsAuthenticated` + `IsPsychologist`)**

| Method + path | Does |
|---------------|------|
| `GET /api/v1/relationships/inbox/` | Pending requests (not expired) |
| `POST /api/v1/relationships/requests/<id>/accept/` | → 200 |
| `POST /api/v1/relationships/requests/<id>/decline/` | Body `{"reason": "<code>"}` (optional) → 200 |
| `GET /api/v1/relationships/patients/` | Current patients |
| `GET /api/v1/relationships/patients/<relationship_id>/` | One current patient; 404 unless own and active |
| `POST /api/v1/relationships/patients/<relationship_id>/end/` | Body `{"reason": "<code>"}` (required) → 200 |
| `GET /api/v1/relationships/history/` | Ended relationships, pseudonym only |
| `GET` / `PUT /api/v1/psychologists/me/availability/` | `{"accepting": bool, "reason": "<code>" or null}` |

## 9. Request and response fields

- **Directory card:** `id`, `full_name`, `gender`, `bio`, `qualifications`,
  `license_issuing_country`, `license_issuing_authority`, `specializations`,
  `languages`, `years_of_experience`, `country`, `city`, `timezone`,
  `is_accepting_patients`, `last_active` (band code). **Never:** `license_number`,
  `last_active_at`, `not_accepting_reason`, email, `approval_status`, other
  admin-only fields. A test asserts the exact key set.
- **Minimal card** (used in the patient's `current/` and `requests/` views when the
  psychologist is no longer approved and active): `id`, `full_name` only.
- **Relationship, patient view:** `id`, `status`, `psychologist` (directory card, or
  minimal card as above; includes the last-active band for a pending request),
  `requested_at`, `expires_at`, `responded_at`, `decline_reason`, `cooldown_until`,
  `ended_at`, `ended_by`, `end_reason`.
- **Inbox item:** `id`, `requested_at`, `expires_at`, `requester` →
  `{pseudonym, preferred_language, timezone, country, gender, age}`.
- **Patient, psychologist view (assigned):** `relationship_id`, `accepted_at`,
  `full_name`, `pseudonym`, `age`, `gender`, `phone_number`, `country`, `city`,
  `preferred_language`, `timezone`. **Never `date_of_birth`** (age only, before and
  after acceptance).
- **History item (psychologist):** `relationship_id`, `pseudonym`, `accepted_at`,
  `ended_at`, `ended_by`, `end_reason`.
- **Availability:** `{"accepting": bool, "reason": "<NotAcceptingReason>" or null}`.

## 10. Errors

| Status | Body | When |
|--------|------|------|
| 400 | `{"date_of_birth": ["Add your date of birth to your profile before requesting a psychologist."]}` | Requesting with no date of birth |
| 400 | `{"date_of_birth": ["Your date of birth can't be removed once set."]}` | `PATCH /patients/me/` with `date_of_birth: null` once set |
| 400 | `{"psychologist": ["This psychologist isn't available."]}` | Pending, rejected, deactivated or nonexistent psychologist |
| 400 | `{"psychologist": ["This psychologist isn't accepting new patients right now."]}` | Visible psychologist with the switch off |
| 400 | `{"psychologist": ["You can request this psychologist again on YYYY-MM-DD."]}` | Within the decline cooldown; date of `cooldown_until` in the **patient's** timezone |
| 400 | `{"relationship": ["You already have a psychologist or a pending request."]}` | An open row exists (incl. simultaneous requests) |
| 400 | `{"relationship": ["This request is no longer pending."]}` | Accept/decline/cancel on a non-pending or expired row |
| 400 | `{"relationship": ["You don't have a psychologist right now."]}` | Patient ends with nothing active |
| 400 | `{"reason": ["Choose a reason."]}` | Psychologist ends without a reason |
| 400 | `{"reason": ["Choose a reason when you're not accepting new patients."]}` | Availability off without a reason |
| 400 | `{"confirm": ["Confirm that you want to end this relationship."]}` | `confirm` is anything but JSON `true` |
| 400 | DRF "not a valid choice" | Unknown reason code |
| 401 / 403 / 404 / 429 | DRF defaults | No login / wrong role / not yours or not visible / rate-limited |

## 11. Privacy and who sees what

| Viewer | Sees | Enforced by |
|--------|------|-------------|
| Psychologist with a pending request | pseudonym, preferred language, timezone, country, gender, age | `requester_summary()` (narrow selector, never the general one) |
| Assigned psychologist (accepted row; psychologist approved and active) | real name and profile (§9), **age not date of birth**, unlogged | `is_assigned_psychologist()` + psychologist selectors scoped to own accepted rows |
| Former psychologist (row ended) or paused psychologist | pseudonym only (history); no profile | access ends the moment the row leaves `accepted` or the psychologist stops being approved and active |
| Patients browsing | directory cards of approved, active psychologists; no `not_accepting_reason` | directory selector + serializer |
| Anyone else | unchanged from Phase 2 | — |

The directory is for logged-in patients only. Psychologists who aren't accepting
still appear, flagged, and can't be requested. The Phase 2 admin `identity_reveal`
rule is unchanged.

Defence wording: **"Access ends when care ends; psychologists remain bound by their
professional confidentiality duties."**

## 12. Throttles, page sizes, caching

- Directory: `UserRateThrottle` scope `directory`, **60/min** per user.
- Request creation: `UserRateThrottle` scope `relationship_requests`, **10/hour** per
  user.
- These are per-user (not per-IP), so the unset `NUM_PROXIES` doesn't affect them.
- Pagination: page-number, default 20, `page_size` param, max 50 (directory,
  patient request history).
- `/stats/public/` keeps its 5-minute cache; tests clear the cache.

## 13. Activity tracking

- `ActivityTrackingJWTAuthentication` (subclass of simplejwt's `JWTAuthentication`)
  becomes `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`. After a successful
  authentication it calls `record_activity(user)`.
- Not recorded on `/accounts/refresh/` or `/accounts/logout/`.
- Psychologists only; role checked before any cache or database access.
- 15-minute cache key; cache errors never break authentication.
- Any authenticated request counts as activity.
- `last_active_at = null` → band `never`; frontends label it **"Not active yet"**.

## 14. Audit and logging

`core.audit.log_relationship_event(*, event, relationship_id, actor_id, actor_role,
reason=None)` writes one JSON line to `mindcare.audit`: `event_type:
"relationship"`, `event`, `relationship_id`, `reason`, `actor_id`, `actor_role`,
`timestamp`. Events: `requested`, `cancelled`, `accepted`, `declined`, `expired`,
`ended`. Expiry and system endings log `actor_role: "system"`, `actor_id: null`.
**Never logs `patient_id` and `psychologist_id` together, never names, never
anything a person typed.**

## 15. Admin

- `CareRelationshipAdmin`: read-only (no add, change or delete permission); lists
  status, timestamps, reasons and `ended_by`; shows the patient by **pseudonym**.
  Docstring notes the `PROTECT` consequence.
- `UserAdmin.save_model` calls `end_for_unavailable_account(user)` when `is_active`
  turns off or `approval_status` becomes `rejected` (not when it becomes `pending`).

## 16. Hooks into existing code

- `patients.selectors.get_patient_display_identity()` uses the real
  `is_assigned_psychologist()`.
- `patients.services.update_patient_profile()` enforces the date-of-birth rule (§6.9).
- `stats.selectors` `people_in_care` per §7.
- `config/settings/base.py`: default authentication class; throttle rates
  `directory: "60/min"`, `relationship_requests: "10/hour"`; `apps.relationships` in
  `LOCAL_APPS`; `"relationships"` in `API_V1_APPS`.
- `docs/deployment.md`: test-data cleanup SQL (§18).

## 17. Testing

Service tests first (CLAUDE.md). Plus:

- **Requests:** no date of birth → 400 `date_of_birth`; pending, rejected,
  deactivated and nonexistent psychologist → the same generic 400; not accepting →
  400; open row → 400; cooldown day 29 blocked / day 30 allowed; **stale pending
  (mocked clock past `expires_at`) expired in the same transaction as the new
  request**; simultaneous-request `IntegrityError` → 400.
- **Answering:** another user's row → 404; not pending → 400; accept while switch
  off works; **a deactivated psychologist can't accept**.
- **Races (select_for_update):** accept vs cancel; patient-end vs psychologist-end —
  exactly one succeeds.
- **Ending:** reason validation per `ended_by` (`subscription_lapsed` system-only;
  `patient_unresponsive` rejected as invalid); `end_for_unavailable_account` on
  deactivation and on rejection ends accepted / expires pending; **becoming
  `pending` pauses** (row stays accepted, psychologist loses access, patient sees
  minimal card, not counted in `people_in_care`, patient can still end).
- **Availability:** reason required off, cleared on.
- **Activity:** psychologists only; cache hit skips; Redis error skips silently;
  not on refresh/logout.
- **Date of birth:** corrected yes, cleared no; age changes live after correction.
- **Selectors:** `is_assigned_psychologist`; display identity real name only for
  the assigned psychologist; `requester_summary` exact keys; directory filters,
  ordering, visibility, **exact card keys**; recent list rules; band boundaries;
  assigned view has `age` and no `date_of_birth`.
- **Privacy with real data:** psychologists A and B each have their own patients
  and each sees only their own; B requesting A's patient by id → 404; when A's
  patient ends the relationship, A's access disappears immediately.
- **Stats:** `people_in_care` reflects accepted relationships once the cache is
  cleared.
- **API:** 401 / 403 / 404 per endpoint; throttles configured; page size capped;
  `confirm` strict-true; schema test covers every new path.
- **Audit:** each event line has the agreed keys and never both patient and
  psychologist ids, never names.
- **Admin:** `CareRelationshipAdmin` read-only with pseudonyms; deactivating in
  `UserAdmin` ends relationships.
- **Migrations:** additive; `makemigrations --check` clean; applied to the local
  Docker database only via the guarded command, then a `psql` schema check.

## 18. Deployment notes

- Production gets the migrations through Render's build command after merge.
- No breaking change to any existing endpoint. One behaviour change:
  `PATCH /patients/me/` with `"date_of_birth": null` returns 400 once a date of
  birth is set.
- Test-data cleanup SQL for `docs/deployment.md` (run against the target database,
  in this order, scoped to the test user ids):
  ```sql
  DELETE FROM relationships_carerelationship
   WHERE patient_id IN (SELECT id FROM patients_patientprofile WHERE user_id IN (<ids>))
      OR psychologist_id IN (SELECT id FROM psychologists_psychologistprofile WHERE user_id IN (<ids>));
  DELETE FROM patients_patientprofile WHERE user_id IN (<ids>);
  DELETE FROM psychologists_psychologistprofile WHERE user_id IN (<ids>);  -- M2M rows cascade
  DELETE FROM ngo_ngoprofile WHERE user_id IN (<ids>);                     -- service areas cascade
  DELETE FROM accounts_user WHERE id IN (<ids>);
  ```

## 19. Frontend notes

**MindCare Web (psychologist):** inbox (with requester summary, `expires_at`),
accept, decline (optional reason picker), current patients and patient detail,
history (pseudonym only), availability switch with reason picker, end-relationship
reason picker (`treatment_completed`, `referred_elsewhere`, `other`). Show
`never` as "Not active yet".

**MindCare App (patient):** directory with filters and pagination; psychologist
detail; send request; current request/relationship with the psychologist's
last-active band and `expires_at`; cancel; end relationship (confirmation step,
sends `confirm: true`); request history (decline reason, cooldown date); recent
psychologists; a **date-of-birth screen** shown when a request returns
`{"date_of_birth": [...]}` (check the key, not the text); friendly text for every
reason and band code. `PATCH /patients/me/` with `"date_of_birth": null` returns 400
once a date of birth is set.

## 20. Open risks

1. **Requests can expire unseen until Phase 10** (no emails yet). Accepted for
   development (no live users); 3-day expiry kept.
2. **Pause UX:** what a patient sees while their psychologist is under re-review is
   undecided (Phase 2.5).
3. **Stripe availability in Pakistan** is unconfirmed; Stripe is test-mode only for
   this prototype, so this is a launch-time check, not a blocker.
4. **`NUM_PROXIES` is unset on Render**, affecting anonymous throttles (register,
   login, reference, stats); Phase 3's throttles are per-user.
5. **App registration from a real device is untested** (Flutter build stalled).
6. **The pasted AI-pipeline prompt conflicts with project-vision §12 on approved
   diet/exercise/sleep suggestions.** The prompt: *"No patient-facing endpoint,
   response payload, or UI should ever return a prediction, a probability, a
   review_flag, a risk class, a suggested diet/exercise plan, or anything derived
   from them — not even after psychologist approval."* Vision §12 lists exercises,
   diet plans and sleep schedules as what the AI recommends, and its workflow ends
   *"Approved Recommendation → Patient App → Patient Follows Recommendation"*.
   The prompt's ban on showing predictions, probabilities, review flags and risk
   classes to patients does **not** conflict (vision §12 doesn't say those reach the
   patient). CLAUDE.md only requires the approval gate ("NEVER let AI-generated
   patient recommendations reach a patient without going through the psychologist
   approval workflow"), which implies approved recommendations may reach the
   patient. **Not resolved here; a Phase 6 item.**
