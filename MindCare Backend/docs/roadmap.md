# Roadmap

Backend build order, in dependency order. Each phase builds on the ones before it.
Update the status column as phases land. See @architecture.md for the module layout
and @decisions.md for the reasoning behind scope and ordering choices.

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Project scaffolding | Done |
| 1 | Auth/RBAC: custom `User` model, JWT auth with rotation + blacklisting, RBAC permission classes, auth audit logging, Django admin panel for approving pending accounts | Done |
| 2 | Patient, Psychologist & NGO profiles; patient privacy (pseudonym, `is_profile_public`, display-identity selector); `GET /stats/public/` | In progress |
| 2.5 | Admin Management (see below) | Not started |
| 3 | Psychologist ↔ Patient relationship (request / accept / decline) | Not started |
| 4 | Appointments & sessions (Zoom metadata) | Not started |
| 5 | Journals & psychologist notes — first PHI-sensitive module. **The DB-backed PHI access audit trail must ship before or with this phase** (see @decisions.md) | Not started |
| 6 | AI recommendation workflow (backend side): psychologist approval gate, stub endpoint calling the separate AI service | Not started |
| 7 | Wearable data ingestion — first phase that actually requires Celery + Redis | Not started |
| 8 | Automated reports | Not started |
| 9 | Payments (Stripe) | Not started |
| 10 | Notifications (Firebase Cloud Messaging); also adds email verification, deliberately deferred from Phase 1 | Not started |
| 11 | Communities (creator approval + moderation) | Not started |
| 12 | NGO onboarding | Not started |
| 13 | Emergency assistance — detection thresholds and escalation rules need real design discussion; do not invent them | Not started |
| 14 | Rewards / XP / badges | Not started |
| 15 | Daily challenges — only if time remains | Not started |

## Phase 2.5: Admin Management

Replaces the Phase 1 stopgap (approving pending accounts through the Django admin
panel) with real API endpoints, and delivers the super-admin workflow deferred from
Phase 1 (see @decisions.md, 2026-09-15).

- **Approval-workflow endpoints** for pending psychologist and NGO accounts:
  list pending accounts, approve, reject.
- **Super-admin workflow:** a super-admin creates sub-admin accounts, promotes a
  sub-admin to super-admin, and may demote themselves.
- **Invariant:** at least one super-admin must always exist. The check is done
  atomically (inside the same transaction as the demotion, with row locking) so
  two concurrent demotions cannot leave the system with zero super-admins.
- **Credential document upload** (deferred from Phase 2, which ships text
  credentials only): psychologists upload license / degree certificates and NGOs
  their registration certificate, for admin review. Includes the
  `integrations/storage_client/` integration (private object storage; Render's disk
  is temporary), short-lived signed URLs for admin-only access, and file type and
  size validation. Any new dependency this needs (e.g. a storage SDK) is proposed
  for approval in this phase.

## Unscheduled

Features from @project-vision.md that are part of the product but **not yet
assigned to a phase**. Listed here so they aren't lost. Assign each one a phase
when its turn comes.

- **Motivation Corner** (@project-vision.md §20): motivational quotes, messages and
  periodic reminders, plus opt-in religious content (Quran / Hadith). The religious
  preference is GDPR Art. 9 special-category data; see @decisions.md.
- **AI Chat Assistant** (@project-vision.md §14): patient-side supportive chat
  (explicitly not a replacement for a psychologist) and a more advanced
  psychologist-side assistant. Backend side is integration with the separate AI
  service.
- **Phone-number login**: logging in with a phone number instead of email, for all
  roles. Needs its own unique, verified field on `User`. It is **not**
  `PatientProfile.phone_number`, which is contact-only (see @decisions.md). Pairs
  naturally with Phase 10's verification work.
