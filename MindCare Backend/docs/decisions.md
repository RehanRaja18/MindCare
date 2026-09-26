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
