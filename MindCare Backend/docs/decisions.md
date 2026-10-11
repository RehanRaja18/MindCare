# Architecture Decisions

## 2026-09-12 - Chose Django + DRF over FastAPI for the core backend
**Why:** Team's Python familiarity, and the need for an admin panel + ORM + built-in auth given the number of entities in this system.
**Alternatives considered:** FastAPI — faster and more "modern" for pure APIs, but would have required building admin tooling, auth, and ORM integration from scratch.

## 2026-09-12 - Chose a modular monolith (Django apps per domain) over microservices
**Why:** Unified backend requirement across MindCare Web and MindCare App, plus the FYP timeline doesn't allow for the operational overhead of running and deploying separate services.
**Alternatives considered:** Microservices per domain (accounts, appointments, payments, etc.) — better long-term scalability and isolation, but far too much infrastructure and deployment complexity for the timeline.

## 2026-09-12 - Kept AI inference as a separate FastAPI service, not merged into the Django monolith
**Why:** Different runtime needs (AI/ML dependencies vs. web framework dependencies) and a clean API boundary between the two services.
**Alternatives considered:** Running inference inside the Django process — simpler deployment, but couples unrelated dependency sets and runtime characteristics together.

## 2026-09-12 - Chose service/selector pattern over strict hexagonal Clean Architecture
**Why:** Pragmatic tradeoff that fits Django's ORM-centric style and avoids repository-interface boilerplate that fights the framework.
**Alternatives considered:** Hexagonal/Clean Architecture with repository interfaces — more testable/portable in theory, but adds significant boilerplate for a Django project of this size and timeline.

## 2026-09-12 - Chose PostgreSQL via Supabase/Neon, Redis via Redis Cloud, hosting via Render
**Why:** Free-tier student budget — these providers offer usable free tiers for a project at FYP scale.
**Alternatives considered:** Self-hosted Postgres/Redis on a VPS — more control, but more setup/maintenance burden and no free tier.

## 2026-09-15 - Auth events logged via structured logging, not a DB-backed audit trail (for now)
**Why:** `core/audit.py` is explicitly not a Django app (see @architecture.md), so it
can't own a model/migration on its own, and building a dedicated `apps/audit` app was
judged out of scope for the auth/RBAC foundation task. Auth events (login, failed
login, logout, token refresh, register) are emitted as structured JSON log lines via
a dedicated `mindcare.audit` logger instead.
**Alternatives considered:** A new `apps/audit` app with a DB-backed `AuditLog` model,
queryable for a future admin security dashboard — deferred, but with a hard
deadline: a DB-backed audit trail for PHI access must ship before or with Phase 5
(journals / clinical notes; see @roadmap.md), the first phase that stores PHI. This
is not contingent on an admin-facing audit view existing first — structured log
lines are acceptable for auth events, not for PHI access.

## 2026-09-15 - Deferred the super-admin promote/demote workflow; only the `is_super_admin` field ships now
**Why:** The auth/RBAC foundation task needed a bootstrap mechanism for the system's
first super-admin before any admin-management endpoints exist, so `User` gets an
`is_super_admin` boolean (default `False`) and `create_superuser()` sets it `True`.
The actual workflow — an existing super-admin creating sub-admin accounts, promoting
a sub-admin to super-admin, a super-admin demoting themselves, and the invariant that
at least one super-admin must always exist (checked atomically to avoid a race) — is
deferred to **Phase 2.5: Admin Management** (see @roadmap.md), which also owns the
admin-approval-workflow endpoints (see the auth/RBAC design doc's Section 2 non-goals,
`docs/superpowers/specs/2026-09-15-auth-rbac-design.md`).
**Alternatives considered:** Building the full promote/demote workflow now — rejected
as out of scope; the auth/RBAC task's job is the foundation (the field), not the
admin-management feature built on top of it.

## 2026-09-26 - Added Phase 2.5 (Admin Management) to the roadmap and gave the PHI audit trail a hard deadline
**Why:** Two Phase 1 deferrals had no owner in the phase list. The super-admin
promote/demote workflow and the admin approval endpoints now belong to Phase 2.5,
placed right after profiles so the Django-admin approval stopgap doesn't last long.
The DB-backed audit trail's trigger was changed from "once an admin audit view needs
it" to "before or with Phase 5", because PHI access has to be auditable from the
first moment PHI is stored. Both are recorded in @roadmap.md.
**Alternatives considered:** Leaving both open-ended until a consumer showed up —
rejected, because nothing in the roadmap would have triggered either one.

## 2026-09-26 - Patient privacy: pseudonym + public flag behind one display-identity selector
**Why:** Patients need to take part in the platform (communities, psychologist
requests) without showing their real name to other users unless they choose to.
Phase 2 gives `PatientProfile` an auto-generated pseudonym (`Patient-` + 6 random hex
characters, unique, never usable for login) and `is_profile_public` (default
`False`). A single selector in `apps/patients/selectors.py`,
`get_patient_display_identity()`, decides which one a viewer sees: the real name if
the profile is public, otherwise the pseudonym. The patient always sees their own real
identity. Two hardcoded exceptions see the real name regardless of the flag:
- **The patient's assigned psychologist.** Normal care relationship, not logged.
- **Any admin.** This covers display identity only (name vs. pseudonym) and never
  gives access to PHI (journals, clinical notes, health data). Every time an admin
  resolves a *private* patient's real identity, an `identity_reveal` event is logged
  via `mindcare.audit` (viewer id, patient id, no names).

Enforcement is split across phases, and the later phases **must** use this selector
and not reimplement the rule:
- **Phase 3** (psychologist ↔ patient relationship) must wire the
  assigned-psychologist exception into `get_patient_display_identity()` once the
  relationship model exists. Until then, psychologists get the pseudonym for private
  profiles like any other viewer.
- **Phase 11** (communities) must show every patient's identity through this
  selector.
- **Phase 11's community-creator application must require `is_profile_public=True`**
  as a precondition. A community creator's story is tied to their real identity.
**Alternatives considered:** Per-viewer permission grants (patient chooses who sees
their name) — more flexible, but much more complex, and a single flag plus fixed
exceptions covers the stated need. Unlogged admin access — rejected under HIPAA's
"minimum necessary" principle; admin identity access is kept but made auditable.

## 2026-09-26 - Pseudonyms are immutable; going public is a permanent disclosure
**Why:** Regenerating the pseudonym when a patient goes back to private would only
partly protect them. The display identity is worked out when content is viewed, so
anything the patient wrote while public would switch to the new pseudonym, and anyone
who saw it before could link the two again from the content itself. Rather than
promise a privacy reset the system can't deliver, the pseudonym never changes and the
API contract states that switching to public is a disclosure that can't be undone:
people who saw the real name may still recognise the patient later. The default of
`is_profile_public=False` is the real protection.

**Open question, owned by Phase 11:** should community content show the author's
identity as of when it was posted, or as of when it is viewed? This decides whether
a post's attribution can ever be separated from a real name, and so whether
pseudonym regeneration could become meaningful. Phase 11 must settle it before it
ships community posting.
**Alternatives considered:** Regenerating the pseudonym on public → private (see
above: partial protection that suggests more privacy than it gives); deferring the
whole question to Phase 11 (rejected for the pseudonym itself, which later phases,
e.g. moderation reports, may reference and so needs to be stable now).

## 2026-09-26 - `GET /stats/public/` ships in Phase 2 with an interim `people_in_care`
**Why:** MindCare Web (PR #10) already calls `GET /stats/public/` for
`{ people_in_care, verified_therapists, cities }`, unauthenticated, and shows 0 until
the endpoint exists. `verified_therapists` (approved psychologists) and `cities`
(from the new profile city field) can be built fully now. `people_in_care` really
means "patients with an accepted psychologist", which needs the Phase 3 relationship
model. Rather than block the endpoint, it ships now using **registered patient count
as a temporary definition**, marked in the code as temporary. **Phase 3 must switch
it** to patients with an accepted psychologist.

**Expected early undercount in `cities` (not a bug):** psychologist and NGO profiles
are created at registration with their city filled in, but patient profiles start
empty and get a city only when the patient fills in their profile later (see the
profile-creation entry below). So for a while after launch, `cities` will reflect
psychologist/NGO locations fully and patient locations only partly. A low
number early on is expected.
**Alternatives considered:** Returning 0 or leaving out `people_in_care` until Phase 3
— rejected, since the frontend already copes with 0 and an honest interim count is
more useful; waiting on Phase 3 for the whole endpoint — rejected, as the other two
counts don't depend on it.

## 2026-09-26 - Profile creation: at registration for psychologist/NGO, auto-created empty for patients
**Why:** Psychologist and NGO accounts are admin-approved (Phase 2.5), and an admin
can only review real material, not just a name. So their registration request
carries the role's credential fields (psychologist: license / qualifications; NGO:
organisation registration details), and `register_user()` creates the `User` and
the profile in one transaction. Patients need no approval and signup on MindCare App
should be quick, so a patient's profile is auto-created empty at registration
(just the pseudonym) and filled in later. Every user of these three roles therefore
always has a profile, and later phases never have to handle a missing one.
`NGOProfile` is pulled forward into Phase 2 (in `apps/ngo`) because of this. The
rest of NGO onboarding stays in Phase 12.
**Alternatives considered:** Empty profiles for everyone, filled in after
registration — rejected for psychologist/NGO, because pending accounts can't log in,
so they'd need a limited "complete your application" access state just to submit
credentials. Creating profiles on first edit — rejected, because every later phase
would then have to handle "no profile yet".

## 2026-09-26 - Pakistan-first, open to international users from day one: hybrid location model + timezone
**Why:** MindCare is a Pakistani hospital's product (its home market), but it is
open to international psychologists and patients from launch, not "international
later". Location is therefore modelled as:
- a `Country` table of all ISO 3166-1 countries, seeded by a data migration from a
  list stored in the repo (no new package), required on every profile;
- a `City` table (country FK, name unique per country ignoring case), **seeded with
  major Pakistani cities**. For other countries users type a city name, which the
  service cleans up (trim, collapse whitespace, compare ignoring case) and matches to
  an existing row or creates one. Remaining duplicates (abbreviations, alternative
  spellings) are fixed by admins in Django admin.

`/stats/public/`'s `cities` counts distinct `City` rows used by at least one profile.
Every profile also stores an IANA `timezone` now, because Phase 4 schedules sessions
across timezones and backfilling one later would be awkward. Psychologist
credentials record the **issuing country and issuing authority** alongside the
license number: licenses are jurisdiction-specific, and an admin can't verify one
without knowing where it was issued.

The religious content in the motivation corner (Quran / Hadith recitations and
readings) reflects the product's Pakistan-first, Islamic identity. It stays
**opt-in** as specified in @project-vision.md §20, which also keeps it appropriate for
international users.
**Alternatives considered:** Free-text city (breaks the distinct-city count and Phase
13's region matching); a fully controlled global city list (~150k rows, needs an
outside dataset or package); Pakistan-only controlled list (blocks international users).

## 2026-09-26 - FYP defence note: data minimisation serves both HIPAA and GDPR
**Why:** Because international patients (including EU residents) are in scope, GDPR
applies alongside HIPAA. Several design choices already made serve both, and are
worth stating explicitly in the FYP defence write-up:
- **Pseudonym by default** (`is_profile_public=False`): other users see no real
  identity unless the patient chooses otherwise (data minimisation / "minimum necessary").
- **Admin identity access is narrow and audited**: identity only, never PHI, and every
  reveal of a private patient's identity is logged (`identity_reveal`).
- **PHI never in application logs**; a DB-backed PHI access audit trail is due with Phase 5.
- **Opt-in religious-content preference**: under GDPR Art. 9 a stored preference that
  reveals religious belief is *special category* data, so when the motivation corner
  is built this preference must be opt-in, minimal, and treated as sensitive, not as
  an ordinary setting.
**Alternatives considered:** — (records existing choices for the write-up; nothing new decided).

## 2026-09-26 - Phase 2 patient profile holds demographics only; no health data before the Phase 5 audit trail
**Why:** The DB-backed PHI access audit trail is due with Phase 5 (see above), so
Phase 2 must not store health information. The Phase 2 `PatientProfile` holds identity,
demographics and preferences only: pseudonym, `is_profile_public`, country/city,
timezone, and optional `date_of_birth`, `gender`, `phone_number`,
`preferred_language`. Deliberately left out:
- **Presenting concerns, diagnoses, medications, history.** Clinical data, so it
  goes to Phase 5 behind the audit trail.
- **Emergency / trusted contacts.** Third parties' personal data, collected for
  escalation, so it moves to **Phase 13** and is designed with the emergency flow.
- **Bio and avatar.** An avatar needs file storage (Phase 2.5); a free-text bio is
  exactly where patients would write health details, so both are left out for now.

Strictly, under HIPAA a name plus date of birth held by a healthcare provider is
already PHI. Phase 2 follows the narrower working definition in @../CLAUDE.md (names,
journals, clinical notes, health data) and relies on the protections already in place
(pseudonym by default, audited admin identity access, no PHI in logs).
**Alternatives considered:** A fuller intake profile in Phase 2 (concerns, history,
emergency contacts) — rejected, since it would store health data and third-party
contacts three phases before they can be audited or properly designed.

## 2026-09-26 - `PatientProfile.phone_number` is a contact field, not a login identifier
**Why:** `PatientProfile.phone_number` exists so the patient can be contacted. It is
**not** the deferred phone-number-login feature, which is recorded here for the first
time and is unscheduled (see @roadmap.md). Phone login has to work across every role,
so it would need its own field on `User` (unique, verified), not on a role-specific
profile. The two must stay separate fields: a contact number has no uniqueness or
verification requirement, and merging them would force login rules onto a contact
field (or the reverse). The model carries a comment saying the same.
**Alternatives considered:** Reusing `PatientProfile.phone_number` for login later —
rejected: patient-only, unverified, and not unique.

## 2026-09-26 - Gender and date of birth never go through the general display-identity selector
**Why:** `gender` and `date_of_birth` exist on `PatientProfile` from Phase 2, but
`get_patient_display_identity()` (used for ordinary community content such as posts
and comments) must **never** return them. Age + gender + city next to a pseudonym is
a well-known re-identification combination and would undo the anonymity the pseudonym
exists to provide.

**Phase 11 design note:** the outing / volunteer-matching feature
(@project-vision.md §24, an unscheduled Phase 11 sub-feature) has a real safety need
to show gender and approximate age when strangers arrange to meet. It must use its
**own narrow query**, scoped to that matching context, that exposes gender and an
**approximate age (e.g. an age band), never the exact `date_of_birth`**. It must not
widen the general selector. How approximate, and who in the match sees it, is for
Phase 11 to decide; Phase 2 only ensures the fields exist.
**Alternatives considered:** Adding optional demographic fields to the general
selector — rejected for the re-identification risk above.

## 2026-09-26 - Adults only (18+), self-declared at registration; minors explicitly out of scope
**Decision:** Registration requires an explicit "I confirm I am 18 or older"
declaration. The backend rejects registration without it, and stores the time it was
made on the account (`User.adult_confirmed_at`) so it can be audited. `date_of_birth`
stays optional (see above), but if a patient enters one, it must show them as 18 or
older or validation rejects it.

**Why minors are out of scope** (for citation in the FYP defence):
1. **Pakistani law.** The age of majority is 18. A minor generally can't consent to
   treatment alone, so a psychologist could not lawfully take a minor on as a client
   through the platform without a guardian's involvement.
2. **GDPR parental-consent thresholds.** Since international users (including EU
   residents) are in scope, GDPR Art. 8 requires parental consent to process a
   child's data on the basis of consent below an age each member state sets between
   13 and 16. Supporting that means verifying the parent and recording consent for
   each jurisdiction.
3. **Conflict with the privacy design.** Guardians commonly have rights to see a
   minor's health records (as under HIPAA's parent-as-personal-representative rule).
   That directly contradicts the promise that the patient journal belongs to the
   patient (@project-vision.md §11) and the pseudonym-by-default identity system.
   Supporting minors would mean redesigning both around guardian access, not
   adding a flag.
4. **Scope.** Doing it properly needs guardian accounts, consent records,
   guardian-visibility rules and psychologist obligations. That's a subsystem of
   its own, beyond the FYP timeline.

Self-declaration is the standard approach for adult-only telehealth services. It is
self-reported, which is an accepted limitation. A required date of birth would be
equally self-reported, so it wouldn't be more reliable, and it would slow signup.
**Alternatives considered:** Required date of birth checked to be 18+ (no more
reliable than a declaration, and reverses the optional-DOB decision); minors with
guardian consent (see reasons 1–4).

## 2026-09-26 - Psychologist profile fields, visibility, and a placeholder specialization list
**Decision:** The psychologist profile is sent at registration with: license number
(**admin-only**), issuing country, issuing authority, qualifications,
specializations (at least one), years of experience, languages (at least one),
country / city / timezone, and optional gender and professional bio. Everything
except the license number is visible to patients (the Phase 3 directory). The
consultation fee goes to Phase 9. License numbers are **unique per
`(issuing_country, license_number)`**. A duplicate is rejected with a general error
that doesn't confirm who holds the license.

`Specialization` (and `Language`) are **DB-backed, admin-editable tables**, the same
pattern as `City`: seeded once by a data migration, then corrected in Django admin
with no code change or new migration. Entries are retired with an `is_active` flag,
not deleted, so existing profiles never point to a missing row.

**The seeded specialization list is a PLACEHOLDER, not a finished taxonomy.** It
must be reviewed by an actual clinical advisor before real launch. Starter list:
anxiety, depression, trauma / PTSD, couples / relationship, grief, addiction /
substance use, stress management, OCD, eating disorders, sleep issues, anger
management, family therapy.
**Alternatives considered:** Free-text specializations (can't be filtered reliably in
Phase 3); a `TextChoices` list baked into code (every correction becomes a code
change plus a migration).

## 2026-09-26 - NGO profile fields and country-or-city service areas
**Decision:** The NGO profile is sent at registration with: organisation name,
registration number (**admin-only**), registration country, registering authority,
headquarters country / city / timezone, official phone and email (admin-only for now;
Phase 13 decides who else sees them), optional website and description, and **at
least one service area**. The account holder (`User.full_name`) is the NGO's
representative, not the organisation itself. Registration numbers are **unique per
`(registration_country, registration_number)`**, matching the psychologist license rule.

A **service area** is a country plus an optional city. **No city means the whole
country.** So a national NGO covers all of Pakistan with one row, and a local one
lists specific cities. The service areas are what Phase 13 will match on, since it
alerts NGOs "according to the region". Headquarters location alone would not do.

**Deliberately not collected:** the kinds of emergency support an NGO offers (crisis
line, ambulance, shelter, etc.). That belongs to Phase 13's escalation design, which
must not be invented ahead of time.

`Language` follows the `City` / `Specialization` pattern (DB-backed, seeded with
ISO 639-1, admin-editable). The product interface is English-only: `Language`
records the languages a psychologist can hold sessions in (and a patient's
preferred session language); it is not interface translation and is not
enforced on text input. The 18+ declaration (`User.adult_confirmed_at`) applies
to **all** public registration roles.
**Alternatives considered:** City-only service areas (forces national NGOs to list
every city); headquarters-only location (can't represent where an NGO operates).

## 2026-09-26 - Credential fields are locked after registration; Phase 2 access and API-shape choices
**Decision:** Once registered, the fields an admin reviews for approval can't be
changed through the API: psychologist `license_number`, `license_issuing_country`,
`license_issuing_authority`, `qualifications`; NGO `registration_number`,
`registration_country`, `registering_authority`, `organization_name`. A profile
update that tries to change them is rejected. Every other field (bio, languages,
specializations, city, service areas, etc.) stays editable. Real corrections are
made by an admin in Django admin for now, until Phase 2.5 adds a "request credential
change → re-review" flow (see @roadmap.md).
**Why:** If credentials could be edited after approval, the approval would no longer
guarantee that the credentials an admin checked are the ones on the account. Sending
the account back to `pending` on any edit would lock working psychologists out over
typo fixes before Phase 2.5 has the review tools to clear them quickly.

**Also settled for Phase 2:**
- **Access:** a profile can be read and edited only by its owner and by admins.
  There is no psychologist directory for patients and no psychologist access to
  patient profiles until Phase 3 adds the relationship-based ownership check.
- **`/stats/public/`:** anonymous rate limiting plus a cache of about 5 minutes, so
  an unauthenticated endpoint that counts across tables can't be used to overload
  the database.
- **Register request shape:** `POST /api/v1/accounts/register/` keeps its path and
  takes a nested `profile` object whose fields depend on `role`. This is a
  contract change both frontends must adopt.
**Alternatives considered:** Returning to `pending` on credential edits (too harsh
without Phase 2.5 tooling); allowing edits and only logging them (approval stops
guaranteeing anything).

## 2026-09-27 - Phase 6 must store the full recommendation triple, and needs separate training-use consent
**Decision (for Phase 6, recorded now so it isn't lost):** Every AI recommendation
record must store three things as **distinct fields**, not only the final result:
1. **The input**: the patient data snapshot sent to the AI service to produce the
   suggestion. A snapshot, not a live reference, because the profile and other
   inputs will change later.
2. **The AI's raw suggestion**, exactly as the AI service returned it.
3. **The psychologist's final version**: approved unchanged, or modified (and
   rejected, if Phase 6 allows rejection).

**Why:** This triple (input → AI suggestion → psychologist's correction) is the
training data for future model improvement described in @project-vision.md §13.
If only the approved result is stored, the feedback signal (what the psychologist
changed and why) is lost for good, and records from before the fix can't be
reconstructed.

**Consent precondition. Must be resolved before Phase 6 is built:** Using a
patient's data to improve the model is a **different purpose** from producing a
recommendation for that patient. The patient consent wording must cover
future-model-improvement use **explicitly and separately** from consenting to
receive recommendations. Under GDPR this is a separate processing purpose that needs
its own lawful basis, and health data is special-category data (Art. 9). Under
HIPAA, using PHI beyond treatment needs its own authorisation or de-identification.
Patients who decline training use must still be able to receive recommendations, and
their triples must be excluded from any training export.

**Deliberately not decided now:** retraining mechanism, model versioning, evaluation
and validation process, de-identification method for training exports, and
deployment of retrained models. @project-vision.md §13 says these need careful
design; they are a full design task for when Phase 6 is actually underway.
**Alternatives considered:** Storing only the final approved recommendation, which
loses the feedback signal permanently; treating recommendation consent as covering
training use, which conflates two purposes and isn't defensible under GDPR or HIPAA.

## 2026-09-27 - Phase 6: AI-assisted recommendations only for patients aged 18–50; unknown age means manual-only
**Decision (Phase 6 forward-note; related to the 18+ registration decision and the
recommendation-triple entry above):** AI-assisted recommendations are limited to
patients aged **18–50**, the population the model is trained and validated for.
Patients over 50 register normally and use the whole platform, but get
**psychologist-only manual recommendations**. For them the AI step is **skipped
entirely**, not just deprioritised.

**Eligibility requires positive evidence.** It depends on `date_of_birth`, which
stays optional at registration. A patient with no `date_of_birth` on file gets the
manual-only flow, the same as a patient confirmed to be outside 18–50. Unknown age
is **never** treated as AI-eligible.

**Updated 2026-10-06 (Phase 3):** a patient must have a `date_of_birth` before they
can request a psychologist, and once set it can be corrected but never cleared (see
the Phase 3 entries below). So **every patient who has a psychologist always has a
date of birth**. The manual-only fallback for a missing date of birth now covers
only patients who never requested a psychologist.

**How Phase 6 must apply this:**
- **The check runs in the backend before any call to the AI service.** An
  ineligible patient's data is never sent to the AI service at all, not even to be
  thrown away afterwards.
- **Age is calculated when the recommendation is generated**, not at registration.
  A patient who turns 51 moves to manual-only from then on. Working reading of
  "18–50": whole years, inclusive, so eligible from the 18th birthday until the day
  before the 51st. Confirm this when Phase 6 is designed.
- **Each recommendation records whether AI was used and why** (e.g. `ai_used`,
  plus a reason such as `no_date_of_birth` / `outside_validated_age_range`). For a
  manual-only recommendation, the AI-suggestion field of the triple is empty, not
  filled with placeholder data. This keeps the training data clean and makes the
  gate auditable.
- The psychologist dashboard should say *why* AI assistance isn't available for a
  patient (e.g. "no date of birth on file"). That's a UX note for Phase 6, not a
  backend rule.

`date_of_birth` is self-reported and the patient can edit it (validated 18+ when
set), so eligibility is only as reliable as what the patient declares. This is the
same accepted limitation as the 18+ declaration. Under-18s remain fully out of scope
under the 18+ registration decision; they are not a separate case here.
**Why:** It avoids claiming the model is valid for a population outside the range
it was trained and evaluated on. Defaulting unknown age to manual-only means a
missing field can never quietly put a patient into an unvalidated AI flow.
**Alternatives considered:** Making `date_of_birth` required (rejected; that reopens
the quick-signup decision); treating unknown age as eligible (rejected; eligibility
would then depend on missing evidence, not positive evidence); showing AI
suggestions for over-50s with a warning (rejected; it still presents unvalidated
model output to a psychologist as if it were valid).

## 2026-09-27 - Resolved: patients send `profile.timezone` at registration, set automatically by the device
**Decision:** The patient register request includes `profile.timezone` (required,
IANA name). MindCare App reads it from the device, so the patient never types or
picks it. This resolves the open question raised in the Phase 2 spec review
(2026-09-26), where two earlier entries seemed to conflict: patient profiles are
"auto-created empty (just the pseudonym)", while "every profile stores an IANA
`timezone`".
**Why:** The "quick signup" goal behind the empty patient profile was about
**avoiding manual data entry**, not about keeping the profile empty for its own sake.
A value filled in automatically adds no friction, so it doesn't reopen the
empty-profile decision. Every other patient field is still filled in later by the
patient.
**Alternatives considered:** A server-side default of `Asia/Karachi` (a guess that
would silently mis-schedule international patients in Phase 4); leaving it empty
until the patient sets it (every Phase 4 scheduling path would then have to handle a
missing timezone).

## 2026-09-28 - Tests never inherit `DATABASE_URL`; they run only against a local, disposable Postgres
**Decision:** `config/settings/test.py` sets its own `DATABASES` from
`TEST_DATABASE_URL`, defaulting to the docker-compose `db` service
(`localhost:5432/mindcare`), and raises `ImproperlyConfigured` if the host isn't
`localhost`, `127.0.0.1` or `::1`. There is deliberately **no override flag**.
**Why:** `DATABASE_URL` in a developer's `.env` can point at the production Supabase
project. Before this change the test settings inherited it, so every test run would
create and drop a `test_<name>` database on that server. Tests must never be able to
reach production. The guard makes a misconfiguration fail loudly before any
connection, instead of silently using a remote database. CI sets `TEST_DATABASE_URL`
to its own localhost Postgres service.
**Alternatives considered:** SQLite for tests (fast, but diverges from Postgres
behaviour this project relies on, such as functional and conditional unique
indexes); a `TEST_DATABASE_URL` without a host guard (one wrong env var away from
the same risk); an escape-hatch flag for remote test DBs (rejected — an override
that exists will eventually be used by accident).

## 2026-09-29 - Phase 11 forward-note: community moderation reports, admin review, and time-limited bans
**Decided (direction for Phase 11):**
- **Reports aggregate per content item, not per user.** Each reported message, post,
  image or video accumulates its own reports.
- **Admin review screen** shows the flagged content, the report reason(s), and lets
  the admin open the surrounding community thread for context before deciding.
- **Admin actions:** *dismiss* (no violation found) or *ban for a fixed period*
  (e.g. 15 days). The ban **lifts automatically** when the period ends.
- **Ban actions are audited:** acting admin (viewer), target user, reason, duration.

**Open choices, not yet made** (Phase 11 must settle these; they were left as
placeholders when this note was written):
1. **Which path surfaces an item to admin review:**
   - *Volume path*: N reports from distinct accounts surface it;
   - *Severity path*: a report tagged with a severity reason (e.g. self-harm,
     threat) surfaces immediately regardless of count;
   - or both together.
2. **Ban scope: account-wide (cannot log in) or community-only.**
   - An account-wide ban on a *patient* would also cut off their psychologist
     sessions, recommendations and emergency assistance (SOS, Phase 13).
   - A community-only ban leaves care access intact.
   - This is a patient-safety decision, not just a moderation one.
3. **Severity reasons that signal risk to the reporter's or poster's safety**
   (e.g. self-harm) may need to reach the emergency / psychologist flow (Phase 13),
   not only the moderation queue. Phase 11 and Phase 13 must decide this together,
   and the thresholds must not be invented (see @project-vision.md §27).

**Also deferred to Phase 11 design:**
- the exact report/volume threshold (N);
- the list of severity reasons;
- whether repeat bans escalate in length;
- whether a banned user is told the reason.

**Why recorded now:** these rules shape the moderation data model: per-item report
aggregation, ban records with an expiry, and an audit trail of ban actions. Writing
them down before Phase 11 keeps them from being rediscovered or reversed. The open
choices are listed explicitly so they aren't mistaken for decisions.
**Alternatives considered:** Per-user report counts (rejected: one bad post
shouldn't be judged against a user's whole history, and it makes pile-on
brigading easier); permanent bans by default (rejected: a fixed period that lifts
automatically is the stated intent).

## 2026-09-29 - Phase 11 forward-note: community feed performance and attachment storage
**Decided (direction for Phase 11):**
- **Paginated message lists.** A bounded page size, never the full history in one
  response.
- **No N+1 queries.** Fetching a page loads author, reactions and attachment
  metadata in one or two round trips (`select_related` / `prefetch_related`), not
  once per message.
- **Short read cache for popular community lists,** the same pattern as
  `GET /stats/public/` (cached for a few minutes, anonymous-safe).
- **Attachments live in object storage (Supabase Storage)** behind
  `integrations/storage_client/`, the same storage integration Phase 2.5 builds for
  credential documents (see @roadmap.md). **The database stores only a reference**
  (URL or file key), never the file bytes.

**Open choice, not yet made** (left as a placeholder when this note was written):
1. **Attachment scope:** *photos only, video deferred*, or *photos and video from
   the start*. If video is deferred, video attachments are explicitly out of scope
   for the FYP, revisited only if time remains after the core roadmap.

**Privacy points Phase 11 must address** (these follow from existing decisions;
they are not new rules):
- **Access to files:** Phase 2.5 credential documents are private, with
  short-lived signed URLs. Phase 11 must choose between the same, or public URLs,
  for community attachments. Patients posting in mental-health communities are
  pseudonymous by default, and a public, guessable file URL would bypass the
  community's own access rules.
- **Metadata in photos:** EXIF data, especially GPS location, can identify a
  patient and would defeat the pseudonym system (see the 2026-09-26
  display-identity and demographics entries). Phase 11 should strip EXIF from
  uploaded images.

**Also deferred to Phase 11 design:**
- the exact page size;
- attachment size and type limits;
- whether attachments need admin moderation review before they become visible
  (see the moderation forward-note above).

**Why recorded now:** pagination, query shape and the storage split determine the
community data model and API contract. The storage integration is shared with
Phase 2.5, so both phases should build on one `storage_client` rather than two.
**Alternatives considered:** Storing files in Postgres (rejected: bloats the
free-tier database and backups, and file serving belongs in object storage);
unpaginated feeds (rejected: responses and queries grow without bound).

## 2026-09-29 - Phase 11 forward-note: soft-delete for community messages and attachments
**Decided (direction for Phase 11):**
- **Deletion is soft-delete, not an immediate hard delete.** Deleting sets
  `deleted_at`. The item disappears from the community feed, but the row and its
  attachment reference stay.
- **Why:** a message under an open moderation report (see the moderation
  forward-note above) must still be visible to the reviewing admin even if its
  author deletes it. Otherwise, deleting would destroy the evidence.
- **Scheduled hard delete.** A scheduled job permanently removes soft-deleted items
  after a fixed window (e.g. 30 days), **unless a report is open against them**.
  Those are kept until the report is resolved and are hard-deleted at the next run
  after that. This matches the data-minimisation position recorded for the FYP
  defence (2026-09-26): deleted content isn't kept indefinitely.
- **Attachment access is revoked at soft-delete time,** separately from the later
  hard-delete cleanup. After soft-delete, no one can fetch the file through normal
  community access. The only exception is an admin reviewing an open report, who
  gets access through an admin-only, short-lived signed URL (consistent with the
  private-storage question in the feed/attachments note above).
- **Copying content** (screenshots, saving an image) happens on the client and
  needs no backend support. The backend can't prevent it, and that limitation
  applies to any messaging system.

**Dependency:** the scheduled hard-delete job needs Celery beat (periodic tasks) on
Redis, which the roadmap first introduces in **Phase 7**. Phase 11 builds on that
and doesn't add its own scheduler.

**Also deferred to Phase 11 design:**
- the exact hard-delete window;
- whether a user can undo a delete within a grace period;
- whether edit history is kept alongside delete (if it is, edits to a reported
  message must stay visible to the reviewing admin, for the same reason as above);
- how a whole-account erasure request (e.g. a GDPR right-to-erasure request)
  interacts with open reports.

**Alternatives considered:** Immediate hard delete (rejected: authors could
destroy reported content before review); soft-delete kept forever (rejected:
conflicts with data minimisation).

## 2026-09-28 - Two new apps (`reference`, `stats`) and direct-call profile orchestration
**Why:** Country/City/Language/Specialization are shared by three profile apps and
`core/` can't own models, so they get one owner, `apps/reference`. `GET
/stats/public/` must live at `/api/v1/stats/` to match the URL contract MindCare
Web already calls, so it gets `apps/stats`, which has no models. `register_user()`
creates each profile by calling that app's service directly inside one
transaction, not through a signal: "every user has a profile, or neither exists"
must stay visible and testable.
**Alternatives considered:** Reference tables in `accounts` (unrelated to auth);
stats in `reports` (wrong URL); `post_save` signals (the rollback guarantee would
depend on a handler that's easy to break without anyone noticing).

## 2026-09-29 - Cities typed at registration are unverified until an admin verifies them; `/stats/public/` counts only vetted profiles' cities
**Decision:** `City` gets `is_verified` (default `False`). Seeded cities (the major
Pakistani ones) are verified by migration 0003. A city typed at registration is
created unverified: it works on the profile that created it (the owner still sees it
in `/me/`, and a second profile typing the same name reuses it), but it is left out
of the public `GET /reference/cities/` dropdown until an admin verifies it in Django
admin (list-editable flag or the "Mark selected cities as verified" action).
`/stats/public/`'s `cities` count now includes only active patients' cities and the
cities of psychologists and NGOs that are active **and** approved; pending, rejected
and deactivated ones don't count.
**Why:** Registration is anonymous, so without this an attacker could publish
arbitrary text into a patient-facing dropdown and inflate a public number with
throwaway registrations. Admin verification and the approval gate put a human
between anonymous input and public output.
**Alternatives considered:** Showing only cities used by approved profiles (an
unapproved profile's city would then never appear, and a city's visibility would
change silently when profiles are approved or deactivated); a character allow-list
only (blocks markup but not spam or false places).

## 2026-09-30 - Phase 13 forward-note: NGOs have no dashboard, by product design
**Decided:** NGOs have **no dashboard**. This is deliberate, not an oversight. An NGO
registers once through the public signup (profile sent at registration, see the
2026-09-26 NGO-profile entry), is approved by an admin, and otherwise does not log in
to operate anything on the platform. Its registered profile (service areas,
headquarters location) exists specifically to be **surfaced to patients during
Phase 13's emergency flow, matched by region** (@project-vision.md §27; service-area
design in the 2026-09-26 entry). **Until Phase 13 exists, an approved NGO account has
no visible effect anywhere in the product. That is expected, not a bug.**

**Consistency notes for Phase 12/13** (existing facts that sit next to this decision,
recorded so they're resolved deliberately rather than by accident):
- **NGO login still exists and is used for one thing.** Approved NGOs can log in, and
  Phase 2 ships owner-only `GET`/`PATCH /api/v1/ngo/me/` so an NGO can keep its
  service areas, contact details and description current (credentials stay locked).
  "No dashboard" therefore means no operational features, not no login. If NGOs
  should never log in, profile upkeep has to move to admins instead; decide in
  Phase 12.
- **Vision §27 also mentions NGOs being *alerted*** ("relevant NGOs … may potentially
  be alerted according to the region"). That is a different flow from surfacing
  NGOs to a patient: alerting needs an outbound channel (e.g. the official phone or
  email, or a Phase 10 notification) and possibly an acknowledgement. Phase 13 must
  decide whether it surfaces NGOs to patients, alerts NGOs, or both. Either way it
  must not invent the thresholds (§27).
- **Contact details are admin-only today.** `official_phone` / `official_email` are
  visible only to the NGO itself and admins ("Phase 13 decides who else sees them",
  2026-09-26). Surfacing an NGO to a patient requires Phase 13 to decide exactly which
  fields a patient sees.
- **Roadmap Phase 12 ("NGO onboarding")** should be re-scoped with this in mind. With
  signup, approval (Phase 2.5) and the profile already in place, what's left for
  Phase 12 is mainly credential documents / re-review (already Phase 2.5) and any
  admin-side NGO management.

**Alternatives considered:** An NGO dashboard (case management, incident inbox) —
not part of the product; an NGO's role is to be found and contacted in an emergency,
not to operate in the app.

## 2026-10-06 - Phase 3: one psychologist at a time, request lifecycle, and limits
**Decision:** (Full design: `docs/superpowers/specs/2026-10-05-phase3-relationships-design.md`.)
- A patient has **at most one open row**: one pending request *or* one accepted
  psychologist, enforced by a conditional unique constraint. To switch, the patient
  ends the current relationship from their profile (with a confirmation step), then
  requests someone else.
- One `CareRelationship` row per request in a new `apps/relationships` app; statuses
  `pending → accepted → ended`, or `pending → declined / cancelled / expired`. Every
  ending goes through one service, `end_relationship()`.
- **Requests expire after 3 days** unanswered (evaluated on read; no job). The
  patient can cancel a pending request.
- A psychologist can **decline** with an optional reason from a fixed list
  (`outside_specializations`, `language_or_timezone_mismatch`,
  `case_type_not_taken`, `other`). A decline starts a **30-day cooldown** before that
  patient can request that psychologist again. Cancel, expiry and endings start no
  cooldown: a psychologist who doesn't want a returning patient can simply decline,
  which starts the cooldown, so a separate post-ending cooldown adds nothing.
- A psychologist can **end** a relationship with a required reason
  (`treatment_completed`, `referred_elsewhere`, `other`). `patient_unresponsive` was
  considered and removed: a vanished patient's care ends through Phase 9's
  subscription lapse.
- Psychologists set **"accepting new patients" on/off** themselves, with a required
  reason (`fully_booked`, `away`, `other`) when off; it never changes on its own.
  Patients see only on/off; the reason stays private. Pending requests are
  unaffected and can still be answered.
- Accounts: deactivated or rejected → their relationships end (`system /
  account_unavailable`) and pending requests expire. A psychologist moved back to
  `pending` (Phase 2.5 re-review) is **paused, not ended**: the row stays accepted,
  they lose access (selectors require approved and active; see 2026-10-07: the
  permission class now returns 403 on every psychologist endpoint), the patient can still end
  it. Phase 2.5 decides what the patient sees during a pause.
- **Relationships are free until Phase 9.**
**Why:** "The patient's psychologist" must mean exactly one person for Phases 4–6 and
9. Short expiry suits patients who need help soon; the cooldown stops repeated
requests to someone who said no; ending on deactivation keeps patients from being
stuck with an unreachable psychologist, while a re-review shouldn't cut off care.
**Alternatives considered:** several psychologists at once (every later phase would
have to pick one); several parallel pending requests (auto-cancel complexity); a
7-day expiry (too slow); ending care whenever a psychologist stops being approved
(too harsh for a temporary re-review).

## 2026-10-06 - Phase 3: who sees what, date of birth at request time, last active
**Decision:**
- **Before accepting**, a psychologist sees only the requester's pseudonym, preferred
  language, timezone, country, gender and **age in whole years** — through a narrow
  selector, never the general display-identity selector. A declined or expired
  request never reveals who the patient was.
- **After accepting**, the assigned psychologist (accepted row, psychologist approved
  and active) sees the real name and profile, but **age, never the exact date of
  birth**. This is the assigned-psychologist exception in
  `get_patient_display_identity()`, unlogged.
- **When care ends, access ends immediately**; the former psychologist sees the
  pseudonym only in their history. Defence wording: "Access ends when care ends;
  psychologists remain bound by their professional confidentiality duties."
- **Date of birth is required to send a request** (400 `{"date_of_birth": ["Add your
  date of birth to your profile before requesting a psychologist."]}`), not at
  registration (the register body stays `{timezone}`). Once set it can be corrected
  but **never cleared**. It stays a field on `PatientProfile`; no new table.
- **Psychologists' "last active"** is shown to patients as bands (`today`,
  `this_week`, `this_month`, `over_a_month`, `never` = "Not active yet"), recorded
  from any authenticated request at most every 15 minutes, for psychologists only.
- The directory is for logged-in patients only and never shows the license number.
**Why:** age, gender, language, timezone and country answer "can I serve this
person?" without identifying them; an exact birth date adds little to that decision
and is a strong identifier. Requiring the date of birth only at request time keeps
signup quick and avoids another breaking change.
**Alternatives considered:** showing the full profile on request (every psychologist
asked, including those who decline, learns who the patient is); exact date of birth
(re-identification risk); requiring date of birth at registration (breaks the
just-reviewed signup contract).

## 2026-10-06 - No free-text notes on requests or declines (for now); rules for any future note
**Decision:** Phase 3 stores **no free text** on relationships: no patient note with a
request, no psychologist note with a decline. If a note is ever added, it must be
**hidden on read once `cooldown_until` passes** (not rely on a background job),
**never logged**, and **never shown in Django admin**.
**Why:** patients would write symptoms in a note, which is health data, and the
2026-09-26 rule says no health data before Phase 5's audit trail. Dropping the notes
means Phase 3 needs no exception to that rule.
**Alternatives considered:** a 500-character patient note with safeguards; a
300-character decline note wiped after the cooldown.

## 2026-10-06 - Phase 9 forward-note: subscriptions plug into the relationship; pro-rata refunds
**Decision (record only):**
- Phase 9 adds `Subscription → CareRelationship` (additive). Lapse calls
  `end_relationship(…, ended_by="system", reason="subscription_lapsed")`; the reason
  exists already. `get_active_relationship()` gains "and paid".
- **Patient ends:** a warning that money already paid isn't refunded; no refund.
- **Psychologist ends:** pro-rata refund for every plan (weekly, monthly, yearly) and
  every end reason: `refund = amount paid for the current period × days left ÷ days
  in the period`. The psychologist is paid for every day worked. A vanished patient's
  subscription simply lapses; an abusive patient is handled by reporting messages
  (admin ban) or ending with the pro-rata refund.
- Mechanism: Stripe partial refunds (`amount`) with Stripe Connect and
  `reverse_transfer=true`, so the psychologist's share is pulled back automatically
  and no "didn't pay back" reporting is needed.
- **Stripe is test mode only for this prototype.** Whether Stripe supports payouts to
  psychologists in Pakistan is a **launch-time check, not a blocker.**
**Why recorded now:** Phase 3's relationship is designed around these hooks so Phase
9 integrates without schema changes to relationships or a restart.

## 2026-10-06 - Forward-notes: misconduct reports, erasure, Phase 5 notes, Phase 10 emails
**Decided direction (record only, build nothing now):**
- **Misconduct reports (both directions):** a patient can report a psychologist for
  misconduct; a psychologist can report a patient's messages. The **moderation app**
  owns report records and submission; **Phase 2.5 admin tools** own review, dismiss
  and ban. A ban calls `end_for_unavailable_account`. Scheduled after Phase 3.
- **Erasure requests:** when a patient asks to be deleted, **anonymise rather than
  delete**: blank the name, email and profile, keep a bare relationship row with dates
  and status. Erasure has legal exceptions, and the row is referenced by psychologist
  history, reports and Phase 9 financial records. We do not delete data completely.
  **Needs legal review before launch.**
- **Phase 5 clinical notes belong to the patient–psychologist pair,** shared across
  all `CareRelationship` rows for that pair (each request creates a new row, so a
  returning patient continues the same notes). Patient X with Dr A and with Dr B have
  separate notes; Dr B never sees Dr A's notes. After care ends, the psychologist
  keeps read access to their **own** notes about the former patient, identified by
  pseudonym; access to the real name and profile ends. Phase 5 decides the details;
  Phase 3 needs no schema change for this.
- **Phase 10:** email the psychologist on each new request and a reminder 3–5 hours
  before it expires (`expires_at` is stored for this; the scheduler comes with Phase
  7); notify the patient when a psychologist ends the relationship.

## 2026-10-07 - Phase 3: paused psychologists get 403 on every psychologist endpoint
**Decision:** Every Phase 3 psychologist endpoint (inbox, accept, decline, current
patients, patient detail, end, history, and `/psychologists/me/availability/`)
requires `IsAuthenticated` + `IsPsychologist` + `IsApprovedPsychologist`, so only an
active, approved psychologist gets through. A psychologist moved back to `pending`
(paused for a Phase 2.5 re-review) gets **403 on all of them, including history**;
the same applies to rejected and deactivated psychologists. This replaces the
original Phase 3 spec §11 line that let a paused psychologist keep a pseudonym-only
history. The Phase 2 `/me/` profile endpoints are unchanged (a pending psychologist
still needs them). The patient side is unchanged: a patient can still end a paused
relationship. **Phase 2.5 may revisit this** when it designs the re-review
experience.
**Why:** One simple rule (approved + active) for every psychologist endpoint is
easier to audit than per-endpoint exceptions. A psychologist under re-review
shouldn't act on, or browse, patient-related data. On the psychologist side, the
`psychologist_inbox()` and `psychologist_patients()` / `psychologist_patient()`
selectors and the `accept_request()`, `decline_request()` and
`psychologist_end_relationship()` services also check approved and active themselves.
`psychologist_history()` and `set_accepting_status()` don't, so for those two the
permission class is the only gate. Patient-side selectors deliberately don't require
it, because a patient must still see and end a paused relationship.
**Alternatives considered:** Letting paused psychologists keep pseudonym-only
history (the original spec §11), rejected for simplicity and least privilege; Phase
2.5 may revisit.

## 2026-10-07 - AI gateway: psychologist-only, nothing stored or logged, new `apps/ai`
**Decision:** `POST /api/v1/ai/anxiety-prediction/` forwards a body to the MindCare
AI service's `POST /predict` (base URL from the `AI_SERVICE_URL` env var; client in
`integrations/ai_service/client.py`, stdlib `urllib`, no new package) and returns
the AI's response unchanged.
- **Approved, active psychologists only** (`IsPsychologist` +
  `IsApprovedPsychologist`); patients get 403. The prediction is decision support
  for a psychologist. Both CLAUDE.md files forbid model output reaching a patient
  without psychologist review, so "any logged-in user" was rejected.
- **The request body is never stored or logged.** It is health data, and no health
  data is stored before the Phase 5 audit trail (2026-09-26). Failures log only the
  exception type or HTTP status. Because nothing is read from or written to a
  patient record, there is no object-level ownership check: the psychologist types
  the values in. When Phase 6 links a prediction to a patient, it needs the
  ownership check, the audit trail, and the recommendation-triple rules
  (2026-09-27).
- **Errors:** timeout (60 s, for Render cold starts), connection error, 5xx, a 4xx
  other than 400/422 (e.g. Render's 404 for a missing service) or a non-JSON answer
  → 503 `{"detail": "The AI service is waking up. Please try again in a minute."}`.
  The AI's 400/422 → 400 `{"detail": "<the AI's message>"}`. Throttle
  `ai_prediction`, 20/min per user.
- **A new `apps/ai` app** (no models, like `apps/stats`) because the URL is
  `/api/v1/ai/`. Phase 6's approval workflow stays in `apps/recommendations`.
- **Age range mismatch (open):** the AI service accepts ages **18–49** and rejects
  others with a 422 (passed through as a 400). The 2026-09-27 Phase 6 note says
  **18–50**. The AI side is the one enforced today. Phase 6 must make the two
  agree (the AI's reason: almost no High cases at 50+ in the data).
- `/patient-summary` (severity tier + recommendation bundle) is not exposed yet.
**Alternatives considered:** any logged-in user (patients would see raw model
output); storing requests for later analysis (health data before the audit trail);
`requests`/`httpx` (a new dependency for one call).

## 2026-10-08 - Motivation Corner: text quotes now, religious content later in its own table; extra CORS origins only from env
**Decision:**
- New `apps/motivation` with `Quote` (text, optional author, optional category
  `hope` / `resilience` / `calm` / `self_care`, `is_active`, `created_at`) on an
  abstract `MotivationalContent` base. Migration 0002 seeds 30 short,
  non-religious quotes (classical or public-domain authors and proverbs). Admins
  add, edit and hide quotes in Django admin; the API reads the database on every
  request, so a change shows up immediately.
- `GET /api/v1/motivation/quotes/` (paginated, `?category=`) and
  `/quotes/random/` for **any logged-in user**, active quotes only, throttle
  `motivation` 60/min per user. Quotes aren't health data or personal data, so
  no ownership check applies.
- **Religious content (Dua / Surah / Hadith, with audio) will be a separate
  model and table**, not a `kind` field on `Quote`. It needs fields quotes don't
  (an audio reference through `integrations/storage_client/`, a source
  reference, a translation), and it may only be shown to patients who opted in.
  That opt-in is GDPR Art. 9 special-category data (2026-09-26). With a separate
  table and separate endpoints, the quotes endpoints can't leak it, and the
  opt-in check lives in one place.
- **CORS:** `CORS_EXTRA_ALLOWED_ORIGINS` (comma-separated env var, unset by
  default) adds origins on top of the pinned Vercel origin in `base.py` and
  `prod.py`. Used to let a local Flutter web build (`http://localhost:5000`) call
  production during a demo. `dev.py` lists `http://localhost:5000` directly
  (local only). No localhost origin is hardcoded for production.
**Why:** a "live from the database" demo needs admin edits to appear at once;
keeping religious content apart makes the opt-in rule structural, not a filter
someone must remember. Credentials aren't sent cross-origin
(`CORS_ALLOW_CREDENTIALS=False`, bearer tokens), so an extra localhost origin
exposes no cookies, but it should still be removed after the demo.
**Alternatives considered:** one content table with a `kind` field (every query
would need an opt-in filter, and audio fields would be empty on most rows);
hardcoding `http://localhost:5000` in `prod.py` (a development origin allowed in
production for good).

## 2026-10-10 - Phase 1 housekeeping: Supabase Data API off, HSTS, measured NUM_PROXIES, ruff only
**Decision:**
- **Supabase Data API is turned off** (done in the dashboard, 2026-10-10). Django
  connects to Postgres directly as the owner and never used it; with it on, any
  `public` table without RLS was readable with the project's anon key. One setting
  covers every future table, which per-table RLS would not. Supabase Storage is a
  separate service and is unaffected.
- **HSTS:** `SECURE_HSTS_SECONDS = 86400` (one day) in `prod.py`, raised to one year
  after a week without problems. No `includeSubDomains`: the host is a subdomain of
  `onrender.com`, which we don't control.
- **`NUM_PROXIES` is measured, not guessed.** DRF reads `X-Forwarded-For` from the
  right. Too low and every client shares one throttle bucket (today, with 0); too
  high and a client can forge its address and slip past the login limit. Requests
  pass through Cloudflare and Render's proxy, and neither documents how many entries
  it adds. A temporary admin-only `GET /api/v1/accounts/debug/client-ip/` shows the
  headers once on production. **Hard rule: that endpoint is removed in the very next
  PR**, whatever else that PR contains.
- **black and flake8 removed from `requirements/dev.txt`.** Pre-commit runs ruff
  (lint and format), so neither tool was ever run; dependabot PRs #21 and #30 are
  closed rather than merged.
**Alternatives considered:** RLS on every table through a migration (must be repeated
for every new table); guessing `NUM_PROXIES=1`; throttling on `CF-Connecting-IP`
(only safe if the origin can never be reached except through Cloudflare).
