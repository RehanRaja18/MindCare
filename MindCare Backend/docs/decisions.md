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
ISO 639-1, admin-editable). The 18+ declaration (`User.adult_confirmed_at`) applies
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
stays **optional** (Phase 2 decision, not reopened here). A patient with no
`date_of_birth` on file gets the manual-only flow, the same as a patient confirmed
to be outside 18–50. Unknown age is **never** treated as AI-eligible.

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
