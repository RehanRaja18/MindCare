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
