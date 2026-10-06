# Phase 3 — Psychologist ↔ Patient Relationships: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Patients find a psychologist, send one request, and once accepted have exactly one active psychologist who sees their real identity (age, never date of birth) for as long as the relationship lasts.

**Architecture:** New `apps/relationships` app with one `CareRelationship` row per request (status lifecycle, conditional unique constraint for "one open row per patient"). All writes go through `relationships/services.py` with `select_for_update()` on state changes; reads through `relationships/selectors.py`. The directory lives in `apps/psychologists`. Activity tracking hooks into a JWT authentication subclass.

**Tech Stack:** Django 6.1, DRF 3.18, simplejwt, drf-spectacular, PostgreSQL (local Docker for tests), pytest-django (`django.test.TestCase` / `TransactionTestCase` / `rest_framework.test.APITestCase`).

**Spec:** `docs/superpowers/specs/2026-10-05-phase3-relationships-design.md` (approved 2026-10-06). Reasoning: `docs/decisions.md` (2026-10-06 entries). Read both before starting.

## Global Constraints

- Branch: `phase-3-relationships`. Never commit to `main`. **Never touch `MindCare Web/` or `MindCare App/`.**
- **Stage files by name only. Never `git add .` / `git add -A`.** Never `git clean`, `reset --hard`, `checkout .`, or `git stash`.
- **Never run `manage.py migrate`, `dbshell`, `runserver` or `manage.py test` against `.env`.** `makemigrations` is fine. Tests only via `venv/Scripts/python -m pytest` (guarded local Docker test DB). The controller applies migrations to local Docker in Task 9.
- No new third-party packages.
- Views are thin: parse → service/selector → serialize. Business rules live in services/selectors.
- No PHI in logs. Relationship audit lines carry `relationship_id`, `event`, `reason`, `actor_id`, `actor_role` only — never `patient_id` and `psychologist_id` together, never names.
- Every task appends its rows to `docs/module-reference.md` in the existing table format (sections alphabetical; add `### apps/relationships` after `### apps/reference`).
- API tests post JSON: `self.client.post(url, data, format="json")`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Pre-commit hooks (ruff, ruff-format) may reformat on commit: after every edit, re-read the edited region to confirm it applied; if a hook reformats and fails a commit, re-stage the same named files and commit again. Never `--no-verify`.
- Exact values (spec §4): expiry **3 days**; decline cooldown **30 days** (declines only); activity cache **15 min**; recent list **10**; page size **20**, max **50**; throttles `directory: "60/min"`, `relationship_requests: "10/hour"` (per user).
- Exact codes (spec §5.2): `RelationshipStatus` = `pending accepted declined cancelled expired ended`; `DeclineReason` = `outside_specializations language_or_timezone_mismatch case_type_not_taken other`; psychologist `EndReason` = `treatment_completed referred_elsewhere other`; patient `patient_ended`; system `account_unavailable subscription_lapsed`; `EndedBy` = `patient psychologist system`; `NotAcceptingReason` = `fully_booked away other`. **No `patient_unresponsive`.**
- Exact error texts: spec §10 (copied into Task 3/4/7/8 code verbatim).
- Psychologist-facing responses **never** include `date_of_birth` (age only).

## File map

| File | Responsibility | Task |
|------|----------------|------|
| `apps/relationships/{__init__,apps,models,admin,services,selectors,permissions,tasks}.py`, `api/{__init__,serializers,views,urls}.py`, `migrations/`, `tests/` | the relationship domain | 1–8 |
| `apps/psychologists/models.py` (+ migration 0002) | `is_accepting_patients`, `not_accepting_reason`, `NotAcceptingReason` | 1 |
| `apps/accounts/models.py` (+ migration 0003) | `User.last_active_at` | 1 |
| `core/testing.py` | `make_patient()`, `make_psychologist()` factories | 1 |
| `core/audit.py` | `log_relationship_event()` | 2 |
| `apps/patients/selectors.py` | real `is_assigned_psychologist` in display identity | 2 |
| `apps/patients/services.py` | date of birth can't be cleared once set | 3 |
| `apps/accounts/admin.py` | `save_model` → `end_for_unavailable_account` | 4 |
| `apps/accounts/authentication.py` | `ActivityTrackingJWTAuthentication` | 5 |
| `apps/psychologists/selectors.py` | directory selectors | 6 |
| `apps/stats/selectors.py` | `people_in_care` from relationships | 6 |
| `core/pagination.py` | `StandardPagination` (20 / 50) | 7 |
| `apps/psychologists/api/*` | directory card + views; availability view | 7, 8 |
| `config/settings/base.py`, `config/urls.py` | app registration, throttles, default auth | 1, 5, 7 |
| docs | architecture, module-reference, roadmap | each task + 9 |

---

### Task 1: Data model — `CareRelationship`, profile/user fields, admin, factories

**Files:**
- Create: `apps/relationships/__init__.py` (empty), `apps.py`, `models.py`, `admin.py`, `services.py` (docstring only), `selectors.py` (docstring only), `permissions.py` (docstring only), `tasks.py` (docstring only), `api/__init__.py` (empty), `api/serializers.py` (docstring only), `api/views.py` (docstring only), `api/urls.py`, `migrations/__init__.py` (empty), `tests/__init__.py` (empty), `tests/test_models.py`, `tests/test_admin.py`
- Modify: `apps/psychologists/models.py`, `apps/accounts/models.py`, `core/testing.py`, `config/settings/base.py` (LOCAL_APPS), `config/urls.py` (API_V1_APPS), `docs/module-reference.md`
- Generated: `apps/relationships/migrations/0001_initial.py`, `apps/psychologists/migrations/0002_*.py`, `apps/accounts/migrations/0003_*.py`

**Interfaces:**
- Produces: `CareRelationship` and constants `REQUEST_EXPIRY = timedelta(days=3)`, `DECLINE_COOLDOWN = timedelta(days=30)`, `OPEN_STATUSES`, `PSYCHOLOGIST_END_REASONS`, `PATIENT_END_REASONS`, `SYSTEM_END_REASONS`; choices `RelationshipStatus`, `DeclineReason`, `EndReason`, `EndedBy` (all in `apps.relationships.models`); `apps.psychologists.models.NotAcceptingReason`; `PsychologistProfile.is_accepting_patients`, `.not_accepting_reason`; `User.last_active_at`; `core.testing.make_patient(*, date_of_birth=None, timezone="Asia/Karachi", **user_extra) -> PatientProfile` (None → born 1995-01-01; pass `date_of_birth=False` for a profile without one); `core.testing.make_psychologist(*, approval_status=ApprovalStatus.APPROVED, is_active=True, full_name=None, **profile_overrides) -> PsychologistProfile`.

- [ ] **Step 1: Scaffold the app**

`apps/relationships/apps.py`:

```python
from django.apps import AppConfig


class RelationshipsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.relationships"
    verbose_name = "Care relationships"
```

Docstring-only files, one line each: `services.py` → `"""Write-path business logic for care relationships."""`; `selectors.py` → `"""Read-path query logic for care relationships (incl. ownership filtering)."""`; `permissions.py` → `"""App-specific DRF permission classes for relationships."""`; `tasks.py` → `"""Celery tasks for relationships. None yet."""`; `api/serializers.py` → `"""DRF serializers for the relationships API."""`; `api/views.py` → `"""DRF views for the relationships API. Thin: parse -> service/selector -> serialize."""`.

`apps/relationships/api/urls.py`:

```python
"""URL routes for the relationships API, included under /api/v1/relationships/."""

app_name = "relationships"

urlpatterns = []
```

Add `"apps.relationships"` to `LOCAL_APPS` in `config/settings/base.py` directly after `"apps.psychologists"`, and `"relationships"` to `API_V1_APPS` in `config/urls.py` directly after `"psychologists"`.

- [ ] **Step 2: Profile and user fields**

In `apps/psychologists/models.py`, add after the `MAX_YEARS_OF_EXPERIENCE` line:

```python
class NotAcceptingReason(models.TextChoices):
    FULLY_BOOKED = "fully_booked", "Fully booked"
    AWAY = "away", "Away / on leave"
    OTHER = "other", "Other"
```

and inside `PsychologistProfile`, after `bio`:

```python
    # Set by the psychologist (Phase 3); never changes on its own. Patients see
    # only on/off; the reason stays on the psychologist's availability endpoint.
    is_accepting_patients = models.BooleanField(default=True)
    not_accepting_reason = models.CharField(
        max_length=20, choices=NotAcceptingReason.choices, null=True, blank=True
    )
```

In `apps/accounts/models.py`, inside `User` after `adult_confirmed_at`:

```python
    # Written only for psychologists (Phase 3 activity tracking, at most every
    # 15 minutes); shown to patients only as a band, never as a timestamp.
    last_active_at = models.DateTimeField(null=True, blank=True)
```

- [ ] **Step 3: The model**

`apps/relationships/models.py`:

```python
"""Care relationships between a patient and a psychologist (Phase 3).

One row per request; the row becomes the relationship once accepted. A patient
has at most one open row (pending or accepted). Every ending goes through
services.end_relationship(). Phase 9 adds Subscription -> CareRelationship.
"""

from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone

REQUEST_EXPIRY = timedelta(days=3)
DECLINE_COOLDOWN = timedelta(days=30)


class RelationshipStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    ENDED = "ended", "Ended"


OPEN_STATUSES = (RelationshipStatus.PENDING, RelationshipStatus.ACCEPTED)


class DeclineReason(models.TextChoices):
    OUTSIDE_SPECIALIZATIONS = "outside_specializations", "Outside my specializations"
    LANGUAGE_OR_TIMEZONE_MISMATCH = (
        "language_or_timezone_mismatch",
        "Language or time-zone mismatch",
    )
    CASE_TYPE_NOT_TAKEN = "case_type_not_taken", "Not taking this type of case"
    OTHER = "other", "Other"


class EndReason(models.TextChoices):
    TREATMENT_COMPLETED = "treatment_completed", "Treatment completed"
    REFERRED_ELSEWHERE = "referred_elsewhere", "Referred to another professional"
    OTHER = "other", "Other"
    PATIENT_ENDED = "patient_ended", "Ended by the patient"
    ACCOUNT_UNAVAILABLE = "account_unavailable", "Account unavailable"
    # Reserved for Phase 9 (subscription lapse); unused in Phase 3.
    SUBSCRIPTION_LAPSED = "subscription_lapsed", "Subscription lapsed"


PSYCHOLOGIST_END_REASONS = frozenset(
    {EndReason.TREATMENT_COMPLETED, EndReason.REFERRED_ELSEWHERE, EndReason.OTHER}
)
PATIENT_END_REASONS = frozenset({EndReason.PATIENT_ENDED})
SYSTEM_END_REASONS = frozenset(
    {EndReason.ACCOUNT_UNAVAILABLE, EndReason.SUBSCRIPTION_LAPSED}
)


class EndedBy(models.TextChoices):
    PATIENT = "patient", "Patient"
    PSYCHOLOGIST = "psychologist", "Psychologist"
    SYSTEM = "system", "System"


class CareRelationship(models.Model):
    # PROTECT: care history can't disappear by accident. Consequence: a user with
    # relationship rows can't be deleted in Django admin; delete the rows first
    # (SQL in docs/deployment.md).
    patient = models.ForeignKey(
        "patients.PatientProfile",
        on_delete=models.PROTECT,
        related_name="care_relationships",
    )
    psychologist = models.ForeignKey(
        "psychologists.PsychologistProfile",
        on_delete=models.PROTECT,
        related_name="care_relationships",
    )
    status = models.CharField(
        max_length=20,
        choices=RelationshipStatus.choices,
        default=RelationshipStatus.PENDING,
    )
    requested_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.CharField(
        max_length=40, choices=DeclineReason.choices, null=True, blank=True
    )
    cooldown_until = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_by = models.CharField(
        max_length=20, choices=EndedBy.choices, null=True, blank=True
    )
    end_reason = models.CharField(
        max_length=40, choices=EndReason.choices, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=Q(status__in=["pending", "accepted"]),
                name="relationships_one_open_per_patient",
            )
        ]
        indexes = [
            models.Index(
                fields=["psychologist", "status"],
                name="relationships_psych_status_idx",
            )
        ]

    def __str__(self):
        return f"Care relationship #{self.pk} ({self.status})"
```

Run: `venv/Scripts/python manage.py makemigrations accounts psychologists relationships`
Expected: three new migrations (`accounts/0003_user_last_active_at.py`, `psychologists/0002_*.py`, `relationships/0001_initial.py`). Re-read each to confirm only the fields above were added.

- [ ] **Step 4: Test factories**

Append to `core/testing.py`:

```python


def make_patient(*, date_of_birth=None, timezone="Asia/Karachi", **user_extra):
    """A patient user + profile. Pass date_of_birth=False for a profile without
    one; by default the patient is born 1995-01-01."""
    from datetime import date

    from apps.patients.services import create_patient_profile

    user = make_user(role=Role.PATIENT, **user_extra)
    profile = create_patient_profile(user=user, timezone=timezone)
    if date_of_birth is not False:
        profile.date_of_birth = date_of_birth or date(1995, 1, 1)
        profile.save(update_fields=["date_of_birth", "updated_at"])
    return profile


def make_psychologist(
    *, approval_status=ApprovalStatus.APPROVED, is_active=True, full_name=None, **profile_overrides
):
    """An approved, active psychologist user + profile with a unique license."""
    from apps.psychologists.services import create_psychologist_profile

    extra = {"approval_status": approval_status, "is_active": is_active}
    if full_name:
        extra["full_name"] = full_name
    user = make_user(role=Role.PSYCHOLOGIST, **extra)
    profile_overrides.setdefault("license_number", f"LIC-{uuid.uuid4().hex[:8].upper()}")
    return create_psychologist_profile(
        user=user, **psychologist_profile_data(**profile_overrides)
    )
```

- [ ] **Step 5: Write failing model + admin tests**

`apps/relationships/tests/test_models.py`:

```python
"""Model-level tests for CareRelationship (constraint and codes)."""

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.relationships.models import (
    PSYCHOLOGIST_END_REASONS,
    REQUEST_EXPIRY,
    CareRelationship,
    EndReason,
    RelationshipStatus,
)
from core.testing import make_patient, make_psychologist


def _row(patient, psychologist, status):
    now = timezone.now()
    return CareRelationship.objects.create(
        patient=patient, psychologist=psychologist, status=status,
        requested_at=now, expires_at=now + REQUEST_EXPIRY,
    )


class OneOpenRowConstraintTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.a = make_psychologist()
        self.b = make_psychologist()

    def test_second_open_row_rejected_by_database(self):
        _row(self.patient, self.a, RelationshipStatus.PENDING)
        for status in (RelationshipStatus.PENDING, RelationshipStatus.ACCEPTED):
            with self.subTest(status=status):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    _row(self.patient, self.b, status)

    def test_closed_rows_do_not_count(self):
        for status in ("declined", "cancelled", "expired", "ended"):
            _row(self.patient, self.a, status)
        _row(self.patient, self.b, RelationshipStatus.PENDING)  # no error
        self.assertEqual(CareRelationship.objects.filter(patient=self.patient).count(), 5)


class CodeListTests(TestCase):
    def test_psychologist_end_reasons(self):
        self.assertEqual(
            {r.value for r in PSYCHOLOGIST_END_REASONS},
            {"treatment_completed", "referred_elsewhere", "other"},
        )

    def test_patient_unresponsive_is_not_a_reason(self):
        self.assertNotIn("patient_unresponsive", EndReason.values)

    def test_new_profile_fields_default(self):
        psych = make_psychologist()
        self.assertTrue(psych.is_accepting_patients)
        self.assertIsNone(psych.not_accepting_reason)
        self.assertIsNone(psych.user.last_active_at)
```

`apps/relationships/tests/test_admin.py`:

```python
"""Django admin for CareRelationship is read-only and shows pseudonyms."""

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.relationships.models import REQUEST_EXPIRY, CareRelationship
from core.testing import make_patient, make_psychologist


class CareRelationshipAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(email="root@example.com", password="strongpass123")
        self.client.force_login(self.root)
        now = timezone.now()
        self.patient = make_patient(full_name="Ayesha Khan")
        self.rel = CareRelationship.objects.create(
            patient=self.patient, psychologist=make_psychologist(),
            requested_at=now, expires_at=now + REQUEST_EXPIRY,
        )

    def test_no_add_change_or_delete(self):
        admin = site._registry[CareRelationship]
        request = RequestFactory().get("/")
        request.user = self.root
        self.assertFalse(admin.has_add_permission(request))
        self.assertFalse(admin.has_change_permission(request, self.rel))
        self.assertFalse(admin.has_delete_permission(request, self.rel))

    def test_changelist_shows_pseudonym_not_name(self):
        response = self.client.get("/admin/relationships/carerelationship/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.pseudonym)
        self.assertNotContains(response, "Ayesha Khan")
```

Run: `venv/Scripts/python -m pytest apps/relationships -q`
Expected: admin tests FAIL (model not registered); model tests PASS once migrations exist (they exercise the DB constraint).

- [ ] **Step 6: Admin**

`apps/relationships/admin.py`:

```python
"""Read-only Django admin for care relationships (support visibility only).

Patients are shown by pseudonym. Rows can't be added, changed or deleted here.
PROTECT on the profile foreign keys means a user with relationship rows can't be
deleted from the User admin; delete the rows first (SQL in docs/deployment.md).
"""

from django.contrib import admin

from apps.relationships.models import CareRelationship


@admin.register(CareRelationship)
class CareRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "patient_pseudonym",
        "psychologist",
        "status",
        "requested_at",
        "responded_at",
        "ended_at",
        "ended_by",
        "end_reason",
        "decline_reason",
    ]
    list_filter = ["status", "end_reason", "ended_by"]
    fields = [
        "status", "requested_at", "expires_at", "responded_at", "decline_reason",
        "cooldown_until", "ended_at", "ended_by", "end_reason",
    ]

    @admin.display(description="Patient")
    def patient_pseudonym(self, obj):
        return obj.patient.pseudonym

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("patient", "psychologist")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

Run: `venv/Scripts/python -m pytest apps/relationships -q` → PASS. Then the full suite `venv/Scripts/python -m pytest -q` → all pass; `venv/Scripts/python manage.py makemigrations --check --dry-run --settings config.settings.test` → "No changes detected".

- [ ] **Step 7: Module-reference + commit**

Add a `### apps/relationships` section to `docs/module-reference.md` (after `### apps/reference`):

```markdown
| `apps/relationships/models.py` | `CareRelationship` | One row per request; becomes the relationship when accepted; one open (pending/accepted) row per patient via `relationships_one_open_per_patient`; profiles referenced with PROTECT | — | MindCare Web, MindCare App |
| `apps/relationships/admin.py` | `CareRelationshipAdmin` | Read-only support view; patients by pseudonym | `/admin/relationships/carerelationship/` | neither (Django admin) |
```

and under `### apps/psychologists` a row: `| \`apps/psychologists/models.py\` | \`PsychologistProfile.is_accepting_patients\`, \`not_accepting_reason\` | Psychologist-set "accepting new patients" switch with a reason (\`fully_booked\`, \`away\`, \`other\`) | — | MindCare Web |`; under `### apps/accounts`: `| \`apps/accounts/models.py\` | \`User.last_active_at\` | Last activity, psychologists only (shown as a band) | — | MindCare App |`.

```bash
git add apps/relationships config/settings/base.py config/urls.py apps/psychologists/models.py apps/psychologists/migrations/0002_*.py apps/accounts/models.py apps/accounts/migrations/0003_*.py core/testing.py docs/module-reference.md
git commit -m "feat(relationships): CareRelationship model, accepting switch and last_active_at fields, read-only admin

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(`git add apps/relationships` names the new app directory only; list the two generated migration files by their actual names.)

---

### Task 2: Relationship audit event, selectors, and the assigned-psychologist identity rule

**Files:**
- Modify: `core/audit.py`, `apps/relationships/selectors.py`, `apps/patients/selectors.py`, `docs/module-reference.md`
- Create: `core/tests/test_relationship_audit.py`, `apps/relationships/tests/test_selectors.py`
- Modify: `apps/patients/tests/test_selectors.py` (replace the "psychologist sees pseudonym until Phase 3" test)

**Interfaces:**
- Consumes: Task 1 models/constants and factories.
- Produces:
  - `core.audit.log_relationship_event(*, event, relationship_id, actor_id, actor_role, reason=None)`; `RELATIONSHIP_EVENTS = {"requested", "cancelled", "accepted", "declined", "expired", "ended"}`.
  - `apps.relationships.selectors`: `psychologist_is_visible(psychologist_profile) -> bool`; `get_active_relationship(*, patient) -> CareRelationship | None`; `is_assigned_psychologist(*, viewer, patient_profile) -> bool`; `requester_summary(*, relationship) -> dict`; `psychologist_inbox(*, psychologist_user)`; `psychologist_patients(*, psychologist_user)`; `psychologist_patient(*, psychologist_user, relationship_id)`; `psychologist_history(*, psychologist_user)`; `patient_current(*, patient_user)`; `patient_requests(*, patient_user)`; `recent_psychologists(*, patient_user, limit=10) -> list[PsychologistProfile]`; `last_active_band(dt, *, now=None) -> str`.

- [ ] **Step 1: Failing tests**

`core/tests/test_relationship_audit.py`:

```python
"""log_relationship_event writes IDs only, never both patient and psychologist ids."""

import json

from django.test import SimpleTestCase

from core.audit import log_relationship_event


class LogRelationshipEventTests(SimpleTestCase):
    def test_payload_keys(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            log_relationship_event(
                event="ended", relationship_id=5, actor_id=9,
                actor_role="psychologist", reason="treatment_completed",
            )
        payload = json.loads(captured.records[0].getMessage())
        self.assertEqual(
            set(payload),
            {"event_type", "event", "relationship_id", "reason", "actor_id", "actor_role", "timestamp"},
        )
        self.assertEqual(payload["event_type"], "relationship")
        self.assertNotIn("patient_id", payload)
        self.assertNotIn("psychologist_id", payload)

    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):
            log_relationship_event(event="viewed", relationship_id=1, actor_id=1, actor_role="patient")
```

`apps/relationships/tests/test_selectors.py`:

```python
"""Selector tests for relationships."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, Role
from apps.relationships import selectors
from apps.relationships.models import REQUEST_EXPIRY, CareRelationship, RelationshipStatus
from core.testing import make_patient, make_psychologist, make_user


def _row(patient, psychologist, status, **extra):
    now = timezone.now()
    defaults = {"requested_at": now, "expires_at": now + REQUEST_EXPIRY}
    defaults.update(extra)
    return CareRelationship.objects.create(
        patient=patient, psychologist=psychologist, status=status, **defaults
    )


class AssignedPsychologistTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()

    def test_only_accepted_row_to_visible_psychologist_counts(self):
        rel = _row(self.patient, self.psych, RelationshipStatus.PENDING)
        viewer = self.psych.user
        self.assertFalse(selectors.is_assigned_psychologist(viewer=viewer, patient_profile=self.patient))
        rel.status = RelationshipStatus.ACCEPTED
        rel.save()
        self.assertTrue(selectors.is_assigned_psychologist(viewer=viewer, patient_profile=self.patient))
        viewer.approval_status = ApprovalStatus.PENDING  # paused (re-review)
        viewer.save()
        self.assertFalse(selectors.is_assigned_psychologist(viewer=viewer, patient_profile=self.patient))

    def test_get_active_relationship_requires_visible_psychologist(self):
        rel = _row(self.patient, self.psych, RelationshipStatus.ACCEPTED)
        self.assertEqual(selectors.get_active_relationship(patient=self.patient), rel)
        self.psych.user.is_active = False
        self.psych.user.save()
        self.assertIsNone(selectors.get_active_relationship(patient=self.patient))


class RequesterSummaryTests(TestCase):
    def test_exact_keys_and_age_not_date_of_birth(self):
        from datetime import date

        patient = make_patient(date_of_birth=date(2000, 1, 1))
        rel = _row(patient, make_psychologist(), RelationshipStatus.PENDING)
        summary = selectors.requester_summary(relationship=rel)
        self.assertEqual(
            set(summary),
            {"pseudonym", "preferred_language", "timezone", "country", "gender", "age"},
        )
        self.assertIsInstance(summary["age"], int)
        self.assertNotIn("date_of_birth", summary)
        self.assertEqual(summary["pseudonym"], patient.pseudonym)


class ListSelectorTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()

    def test_inbox_excludes_expired(self):
        live = _row(self.patient, self.psych, RelationshipStatus.PENDING)
        other_patient = make_patient()
        past = timezone.now() - timedelta(days=4)
        _row(other_patient, self.psych, RelationshipStatus.PENDING,
             requested_at=past, expires_at=past + REQUEST_EXPIRY)
        self.assertEqual(list(selectors.psychologist_inbox(psychologist_user=self.psych.user)), [live])

    def test_psychologist_patients_only_while_visible(self):
        rel = _row(self.patient, self.psych, RelationshipStatus.ACCEPTED)
        self.assertEqual(list(selectors.psychologist_patients(psychologist_user=self.psych.user)), [rel])
        self.psych.user.approval_status = ApprovalStatus.PENDING
        self.psych.user.save()
        self.assertEqual(list(selectors.psychologist_patients(psychologist_user=self.psych.user)), [])

    def test_patient_current_ignores_expired_pending(self):
        past = timezone.now() - timedelta(days=4)
        _row(self.patient, self.psych, RelationshipStatus.PENDING,
             requested_at=past, expires_at=past + REQUEST_EXPIRY)
        self.assertIsNone(selectors.patient_current(patient_user=self.patient.user))

    def test_recent_psychologists_rules(self):
        psychs = [make_psychologist() for _ in range(12)]
        base = timezone.now() - timedelta(days=100)
        for i, p in enumerate(psychs):
            _row(self.patient, p, RelationshipStatus.ENDED, ended_at=base + timedelta(days=i))
        _row(self.patient, psychs[0], RelationshipStatus.ENDED, ended_at=base + timedelta(days=50))  # duplicate psych
        psychs[11].user.is_active = False  # not visible
        psychs[11].user.save()
        _row(self.patient, psychs[10], RelationshipStatus.PENDING)  # current/pending excluded
        recent = selectors.recent_psychologists(patient_user=self.patient.user)
        self.assertEqual(len(recent), 10)
        self.assertEqual(recent[0], psychs[0])  # most recent ending first
        self.assertEqual(len({p.pk for p in recent}), 10)
        self.assertNotIn(psychs[10], recent)
        self.assertNotIn(psychs[11], recent)


class LastActiveBandTests(TestCase):
    def test_bands(self):
        now = timezone.now()
        cases = [
            (None, "never"),
            (now - timedelta(hours=23), "today"),
            (now - timedelta(days=6), "this_week"),
            (now - timedelta(days=29), "this_month"),
            (now - timedelta(days=31), "over_a_month"),
        ]
        for dt, band in cases:
            with self.subTest(band=band):
                self.assertEqual(selectors.last_active_band(dt, now=now), band)
```

In `apps/patients/tests/test_selectors.py`, replace `test_psychologist_sees_pseudonym_until_phase3` with:

```python
    def test_unrelated_psychologist_sees_pseudonym(self):
        self.assertFalse(self._identity(make_user(role=Role.PSYCHOLOGIST))["is_real_name"])

    def test_assigned_psychologist_sees_real_name_unlogged(self):
        from django.utils import timezone

        from apps.relationships.models import REQUEST_EXPIRY, CareRelationship
        from core.testing import make_psychologist

        psych = make_psychologist()
        now = timezone.now()
        CareRelationship.objects.create(
            patient=self.profile, psychologist=psych, status="accepted",
            requested_at=now, expires_at=now + REQUEST_EXPIRY, responded_at=now,
        )
        with self.assertNoLogs("mindcare.audit", level="INFO"):
            result = self._identity(psych.user)
        self.assertEqual(result["display_name"], "Ayesha Khan")
```

Run: `venv/Scripts/python -m pytest core/tests/test_relationship_audit.py apps/relationships/tests/test_selectors.py apps/patients/tests/test_selectors.py -q`
Expected: FAIL (ImportError / missing selectors).

- [ ] **Step 2: Audit function**

Append to `core/audit.py`:

```python


RELATIONSHIP_EVENTS = {"requested", "cancelled", "accepted", "declined", "expired", "ended"}


def log_relationship_event(*, event, relationship_id, actor_id, actor_role, reason=None):
    """A care-relationship state change. IDs and codes only: never names, never
    anything typed by a person, never patient_id and psychologist_id together."""
    if event not in RELATIONSHIP_EVENTS:
        raise ValueError(f"Unknown relationship event: {event!r}")
    payload = {
        "event_type": "relationship",
        "event": event,
        "relationship_id": relationship_id,
        "reason": reason,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": timezone.now().isoformat(),
    }
    logger.info(json.dumps(payload))
```

- [ ] **Step 3: Selectors**

`apps/relationships/selectors.py` (keep the docstring, then):

```python
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, Role
from apps.relationships.models import CareRelationship, RelationshipStatus
from core.validators import age_on

RECENT_LIMIT = 10
_PSYCH_VISIBLE = Q(
    psychologist__user__is_active=True,
    psychologist__user__approval_status=ApprovalStatus.APPROVED,
)


def psychologist_is_visible(psychologist_profile):
    user = psychologist_profile.user
    return user.is_active and user.approval_status == ApprovalStatus.APPROVED


def _user_is_visible_psychologist(user):
    return (
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.role == Role.PSYCHOLOGIST
        and user.is_active
        and user.approval_status == ApprovalStatus.APPROVED
    )


def get_active_relationship(*, patient):
    """The ONE answer to "is this patient in active care?". Phase 9 adds
    "and the subscription is paid" here."""
    return (
        CareRelationship.objects.filter(patient=patient, status=RelationshipStatus.ACCEPTED)
        .filter(_PSYCH_VISIBLE)
        .select_related("psychologist__user")
        .first()
    )


def is_assigned_psychologist(*, viewer, patient_profile):
    if not _user_is_visible_psychologist(viewer):
        return False
    return CareRelationship.objects.filter(
        patient=patient_profile,
        psychologist__user=viewer,
        status=RelationshipStatus.ACCEPTED,
    ).exists()


def _code_name(obj):
    return None if obj is None else {"code": obj.code, "name": obj.name}


def requester_summary(*, relationship):
    """What a psychologist sees before accepting. Never the name, city, phone or
    exact date of birth (docs/decisions.md, 2026-10-06)."""
    p = relationship.patient
    today = timezone.localdate()
    return {
        "pseudonym": p.pseudonym,
        "preferred_language": _code_name(p.preferred_language),
        "timezone": p.timezone,
        "country": _code_name(p.country),
        "gender": p.gender,
        "age": age_on(p.date_of_birth, today) if p.date_of_birth else None,
    }


def psychologist_inbox(*, psychologist_user):
    return (
        CareRelationship.objects.filter(
            psychologist__user=psychologist_user,
            status=RelationshipStatus.PENDING,
            expires_at__gt=timezone.now(),
        )
        .select_related("patient__country", "patient__preferred_language")
        .order_by("requested_at")
    )


def psychologist_patients(*, psychologist_user):
    if not _user_is_visible_psychologist(psychologist_user):
        return CareRelationship.objects.none()
    return (
        CareRelationship.objects.filter(
            psychologist__user=psychologist_user, status=RelationshipStatus.ACCEPTED
        )
        .select_related(
            "patient__user", "patient__country", "patient__city__country",
            "patient__preferred_language",
        )
        .order_by("-responded_at")
    )


def psychologist_patient(*, psychologist_user, relationship_id):
    return psychologist_patients(psychologist_user=psychologist_user).filter(pk=relationship_id).first()


def psychologist_history(*, psychologist_user):
    return (
        CareRelationship.objects.filter(
            psychologist__user=psychologist_user, status=RelationshipStatus.ENDED
        )
        .select_related("patient")
        .order_by("-ended_at")
    )


_PSYCH_CARD_RELATED = (
    "psychologist__user", "psychologist__country", "psychologist__city__country",
    "psychologist__license_issuing_country",
)


def patient_current(*, patient_user):
    return (
        CareRelationship.objects.filter(patient__user=patient_user)
        .filter(
            Q(status=RelationshipStatus.ACCEPTED)
            | Q(status=RelationshipStatus.PENDING, expires_at__gt=timezone.now())
        )
        .select_related(*_PSYCH_CARD_RELATED)
        .prefetch_related("psychologist__specializations", "psychologist__languages")
        .first()
    )


def patient_requests(*, patient_user):
    return (
        CareRelationship.objects.filter(patient__user=patient_user)
        .select_related(*_PSYCH_CARD_RELATED)
        .prefetch_related("psychologist__specializations", "psychologist__languages")
        .order_by("-requested_at")
    )


def recent_psychologists(*, patient_user, limit=RECENT_LIMIT):
    open_psych_ids = CareRelationship.objects.filter(
        patient__user=patient_user,
        status__in=[RelationshipStatus.PENDING, RelationshipStatus.ACCEPTED],
    ).values_list("psychologist_id", flat=True)
    rows = (
        CareRelationship.objects.filter(patient__user=patient_user, status=RelationshipStatus.ENDED)
        .filter(_PSYCH_VISIBLE)
        .exclude(psychologist_id__in=list(open_psych_ids))
        .select_related(*_PSYCH_CARD_RELATED)
        .prefetch_related("psychologist__specializations", "psychologist__languages")
        .order_by("-ended_at")
    )
    seen, result = set(), []
    for row in rows:
        if row.psychologist_id not in seen:
            seen.add(row.psychologist_id)
            result.append(row.psychologist)
            if len(result) == limit:
                break
    return result


def last_active_band(dt, *, now=None):
    if dt is None:
        return "never"
    age = (now or timezone.now()) - dt
    if age < timedelta(hours=24):
        return "today"
    if age < timedelta(days=7):
        return "this_week"
    if age < timedelta(days=30):
        return "this_month"
    return "over_a_month"
```

In `apps/patients/selectors.py`, replace the `_is_assigned_psychologist` stub's body with a delegation (import inside the function to keep app imports one-directional):

```python
def _is_assigned_psychologist(*, viewer, patient_profile):
    # Phase 3: accepted relationship to a currently approved, active psychologist.
    from apps.relationships.selectors import is_assigned_psychologist

    return is_assigned_psychologist(viewer=viewer, patient_profile=patient_profile)
```

Run: `venv/Scripts/python -m pytest core/tests apps/relationships apps/patients -q` → PASS; then the full suite → all pass.

- [ ] **Step 4: Module-reference + commit**

Rows in `### apps/relationships`:

```markdown
| `apps/relationships/selectors.py` | `get_active_relationship()` | The single "is this patient in active care?" check (accepted row, psychologist approved and active); Phase 9 hook | — | neither (internal) |
| `apps/relationships/selectors.py` | `is_assigned_psychologist()` | True only for an accepted row to a currently approved, active psychologist; used by `get_patient_display_identity()` | — | neither (internal) |
| `apps/relationships/selectors.py` | `requester_summary()` | Pre-acceptance view of a requester: pseudonym, language, timezone, country, gender, age (never name/city/phone/date of birth) | `GET /api/v1/relationships/inbox/` | MindCare Web |
| `apps/relationships/selectors.py` | `psychologist_inbox()`, `psychologist_patients()`, `psychologist_patient()`, `psychologist_history()`, `patient_current()`, `patient_requests()`, `recent_psychologists()`, `last_active_band()` | Ownership-scoped reads for both sides | see Tasks 7–8 endpoints | MindCare Web, MindCare App |
```

and under `### core/`: `| \`core/audit.py\` | \`log_relationship_event()\` | Relationship state changes (requested/cancelled/accepted/declined/expired/ended) with relationship id, actor id/role and reason only | — | neither (internal) |`. Update the `get_patient_display_identity()` row to say the assigned-psychologist exception is now live.

```bash
git add core/audit.py core/tests/test_relationship_audit.py apps/relationships/selectors.py apps/relationships/tests/test_selectors.py apps/patients/selectors.py apps/patients/tests/test_selectors.py docs/module-reference.md
git commit -m "feat(relationships): audit event, selectors, live assigned-psychologist identity rule

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Request lifecycle services (request, cancel, accept, decline, expiry) and the date-of-birth rule

**Files:**
- Modify: `apps/relationships/services.py`, `apps/patients/services.py`, `apps/patients/tests/test_services.py`, `docs/module-reference.md`
- Create: `apps/relationships/tests/test_services_requests.py`, `apps/relationships/tests/test_races.py`

**Interfaces:**
- Consumes: Task 1 models/constants, Task 2 `log_relationship_event`, factories.
- Produces (in `apps.relationships.services`): message constants `DOB_REQUIRED`, `NOT_AVAILABLE`, `NOT_ACCEPTING`, `COOLDOWN`, `ALREADY_OPEN`, `NOT_PENDING`, `INVALID_REASON`; `request_psychologist(*, patient_user, psychologist_id) -> CareRelationship`; `cancel_request(*, patient_user, relationship_id) -> CareRelationship`; `accept_request(*, psychologist_user, relationship_id) -> CareRelationship`; `decline_request(*, psychologist_user, relationship_id, reason=None) -> CareRelationship`; internal `_lock(**filters)`, `_expire_if_stale(rel, now) -> bool`. A missing/foreign row raises `django.http.Http404` (DRF renders 404). Rule violations raise `core.exceptions.DomainValidationError`. `apps.patients.services.DOB_CANNOT_CLEAR`.

- [ ] **Step 1: Failing service tests**

`apps/relationships/tests/test_services_requests.py`:

```python
"""Service tests: requesting, cancelling, accepting, declining, expiry."""

from datetime import timedelta
from unittest.mock import patch

from django.http import Http404
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ApprovalStatus
from apps.relationships import services
from apps.relationships.models import (
    DECLINE_COOLDOWN,
    REQUEST_EXPIRY,
    CareRelationship,
    RelationshipStatus,
)
from core.exceptions import DomainValidationError
from core.testing import make_patient, make_psychologist


class RequestPsychologistTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()

    def _request(self, patient=None, psych_id=None):
        return services.request_psychologist(
            patient_user=(patient or self.patient).user,
            psychologist_id=psych_id or self.psych.pk,
        )

    def test_creates_pending_with_three_day_expiry(self):
        rel = self._request()
        self.assertEqual(rel.status, RelationshipStatus.PENDING)
        self.assertEqual(rel.expires_at - rel.requested_at, REQUEST_EXPIRY)

    def test_requires_date_of_birth(self):
        patient = make_patient(date_of_birth=False)
        with self.assertRaises(DomainValidationError) as ctx:
            self._request(patient=patient)
        self.assertEqual(
            ctx.exception.errors,
            {"date_of_birth": ["Add your date of birth to your profile before requesting a psychologist."]},
        )

    def test_same_generic_error_for_unavailable_psychologists(self):
        pending = make_psychologist(approval_status=ApprovalStatus.PENDING)
        rejected = make_psychologist(approval_status=ApprovalStatus.REJECTED)
        inactive = make_psychologist(is_active=False)
        for psych_id in (pending.pk, rejected.pk, inactive.pk, 999999):
            with self.subTest(psych_id=psych_id), self.assertRaises(DomainValidationError) as ctx:
                self._request(psych_id=psych_id)
            self.assertEqual(ctx.exception.errors, {"psychologist": ["This psychologist isn't available."]})

    def test_not_accepting(self):
        self.psych.is_accepting_patients = False
        self.psych.not_accepting_reason = "fully_booked"
        self.psych.save()
        with self.assertRaises(DomainValidationError) as ctx:
            self._request()
        self.assertEqual(
            ctx.exception.errors,
            {"psychologist": ["This psychologist isn't accepting new patients right now."]},
        )

    def test_one_open_row(self):
        self._request()
        with self.assertRaises(DomainValidationError) as ctx:
            self._request(psych_id=make_psychologist().pk)
        self.assertEqual(
            ctx.exception.errors,
            {"relationship": ["You already have a psychologist or a pending request."]},
        )

    def test_stale_pending_is_expired_in_same_transaction(self):
        first = self._request()
        later = first.expires_at + timedelta(minutes=1)
        with patch("django.utils.timezone.now", return_value=later):
            second = self._request(psych_id=make_psychologist().pk)
        first.refresh_from_db()
        self.assertEqual(first.status, RelationshipStatus.EXPIRED)
        self.assertEqual(second.status, RelationshipStatus.PENDING)

    def test_cooldown_after_decline_day_29_blocked_day_30_allowed(self):
        rel = self._request()
        services.decline_request(psychologist_user=self.psych.user, relationship_id=rel.pk)
        rel.refresh_from_db()
        day29 = rel.responded_at + timedelta(days=29)
        with patch("django.utils.timezone.now", return_value=day29):
            with self.assertRaises(DomainValidationError) as ctx:
                self._request()
        message = ctx.exception.errors["psychologist"][0]
        self.assertTrue(message.startswith("You can request this psychologist again on "))
        with patch("django.utils.timezone.now", return_value=rel.responded_at + DECLINE_COOLDOWN):
            self.assertEqual(self._request().status, RelationshipStatus.PENDING)

    def test_no_cooldown_after_cancel(self):
        rel = self._request()
        services.cancel_request(patient_user=self.patient.user, relationship_id=rel.pk)
        self.assertEqual(self._request().status, RelationshipStatus.PENDING)

    def test_simultaneous_request_integrity_error_becomes_400(self):
        from django.db import IntegrityError

        with patch.object(CareRelationship.objects, "create", side_effect=IntegrityError("dup")):
            with self.assertRaises(DomainValidationError) as ctx:
                self._request()
        self.assertIn("relationship", ctx.exception.errors)


class AnswerRequestTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()
        self.rel = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )

    def test_accept(self):
        rel = services.accept_request(psychologist_user=self.psych.user, relationship_id=self.rel.pk)
        self.assertEqual(rel.status, RelationshipStatus.ACCEPTED)
        self.assertIsNotNone(rel.responded_at)

    def test_accept_allowed_while_not_accepting(self):
        self.psych.is_accepting_patients = False
        self.psych.not_accepting_reason = "away"
        self.psych.save()
        rel = services.accept_request(psychologist_user=self.psych.user, relationship_id=self.rel.pk)
        self.assertEqual(rel.status, RelationshipStatus.ACCEPTED)

    def test_other_psychologist_gets_404(self):
        with self.assertRaises(Http404):
            services.accept_request(psychologist_user=make_psychologist().user, relationship_id=self.rel.pk)

    def test_other_patient_cannot_cancel(self):
        with self.assertRaises(Http404):
            services.cancel_request(patient_user=make_patient().user, relationship_id=self.rel.pk)

    def test_deactivated_psychologist_cannot_accept(self):
        self.psych.user.is_active = False
        self.psych.user.save()
        with self.assertRaises(Http404):
            services.accept_request(psychologist_user=self.psych.user, relationship_id=self.rel.pk)

    def test_expired_request_cannot_be_accepted_and_is_marked_expired(self):
        later = self.rel.expires_at + timedelta(seconds=1)
        with patch("django.utils.timezone.now", return_value=later):
            with self.assertRaises(DomainValidationError) as ctx:
                services.accept_request(psychologist_user=self.psych.user, relationship_id=self.rel.pk)
        self.assertEqual(ctx.exception.errors, {"relationship": ["This request is no longer pending."]})
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.EXPIRED)

    def test_decline_with_reason_sets_cooldown(self):
        rel = services.decline_request(
            psychologist_user=self.psych.user, relationship_id=self.rel.pk,
            reason="outside_specializations",
        )
        self.assertEqual(rel.status, RelationshipStatus.DECLINED)
        self.assertEqual(rel.decline_reason, "outside_specializations")
        self.assertEqual(rel.cooldown_until - rel.responded_at, DECLINE_COOLDOWN)

    def test_decline_rejects_unknown_reason(self):
        with self.assertRaises(DomainValidationError):
            services.decline_request(
                psychologist_user=self.psych.user, relationship_id=self.rel.pk, reason="rude",
            )

    def test_cancel_then_accept_is_not_pending(self):
        services.cancel_request(patient_user=self.patient.user, relationship_id=self.rel.pk)
        with self.assertRaises(DomainValidationError):
            services.accept_request(psychologist_user=self.psych.user, relationship_id=self.rel.pk)

    def test_events_logged_with_ids_only(self):
        import json

        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            services.accept_request(psychologist_user=self.psych.user, relationship_id=self.rel.pk)
        payload = json.loads(captured.records[-1].getMessage())
        self.assertEqual(payload["event"], "accepted")
        self.assertEqual(payload["actor_role"], "psychologist")
        self.assertNotIn("patient_id", payload)
```

`apps/relationships/tests/test_races.py` (real concurrency; needs `TransactionTestCase` so each thread gets its own committed view):

```python
"""Concurrency: row locks make conflicting actions mutually exclusive."""

import threading

from django.db import connection
from django.http import Http404
from django.test import TransactionTestCase

from apps.relationships import services
from apps.relationships.models import RelationshipStatus
from core.exceptions import DomainValidationError
from core.testing import make_patient, make_psychologist


def _run_concurrently(*funcs):
    barrier = threading.Barrier(len(funcs))
    results = [None] * len(funcs)

    def runner(i, fn):
        try:
            barrier.wait()
            fn()
            results[i] = "ok"
        except (DomainValidationError, Http404):  # the loser sees the new state
            results[i] = "rejected"
        finally:
            connection.close()

    threads = [threading.Thread(target=runner, args=(i, f)) for i, f in enumerate(funcs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


class AcceptVsCancelRaceTests(TransactionTestCase):
    def test_exactly_one_wins(self):
        patient = make_patient()
        psych = make_psychologist()
        rel = services.request_psychologist(patient_user=patient.user, psychologist_id=psych.pk)
        results = _run_concurrently(
            lambda: services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk),
            lambda: services.cancel_request(patient_user=patient.user, relationship_id=rel.pk),
        )
        self.assertEqual(sorted(results), ["ok", "rejected"])
        rel.refresh_from_db()
        self.assertIn(rel.status, {RelationshipStatus.ACCEPTED, RelationshipStatus.CANCELLED})
```

(Task 4 adds the patient-end vs psychologist-end race to this file.)

In `apps/patients/tests/test_services.py`, replace `test_dob_can_be_cleared` with:

```python
    def test_dob_can_be_corrected_but_not_cleared(self):
        from datetime import date

        update_patient_profile(profile=self.profile, date_of_birth=date(1990, 5, 5))
        update_patient_profile(profile=self.profile, date_of_birth=date(1991, 6, 6))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.date_of_birth, date(1991, 6, 6))
        with self.assertRaises(DomainValidationError) as ctx:
            update_patient_profile(profile=self.profile, date_of_birth=None)
        self.assertEqual(
            ctx.exception.errors,
            {"date_of_birth": ["Your date of birth can't be removed once set."]},
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.date_of_birth, date(1991, 6, 6))

    def test_dob_none_is_fine_when_never_set(self):
        update_patient_profile(profile=self.profile, date_of_birth=None)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.date_of_birth)
```

Run: `venv/Scripts/python -m pytest apps/relationships/tests/test_services_requests.py apps/relationships/tests/test_races.py apps/patients/tests/test_services.py -q`
Expected: FAIL (services missing; clearing still allowed).

- [ ] **Step 2: Implement the request services**

`apps/relationships/services.py` (keep the docstring, then):

```python
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, Role
from apps.patients.models import PatientProfile
from apps.psychologists.models import PsychologistProfile
from apps.relationships.models import (
    DECLINE_COOLDOWN,
    OPEN_STATUSES,
    REQUEST_EXPIRY,
    CareRelationship,
    DeclineReason,
    RelationshipStatus,
)
from core.audit import log_relationship_event
from core.exceptions import DomainValidationError

DOB_REQUIRED = "Add your date of birth to your profile before requesting a psychologist."
NOT_AVAILABLE = "This psychologist isn't available."
NOT_ACCEPTING = "This psychologist isn't accepting new patients right now."
COOLDOWN = "You can request this psychologist again on {date}."
ALREADY_OPEN = "You already have a psychologist or a pending request."
NOT_PENDING = "This request is no longer pending."
INVALID_REASON = "Choose a valid reason."


def _lock(**filters):
    """The row matching filters, locked for this transaction; 404 if none."""
    rel = (
        CareRelationship.objects.select_for_update(of=("self",))
        .filter(**filters)
        .first()
    )
    if rel is None:
        raise Http404
    return rel


def _expire_if_stale(rel, now):
    if rel.status == RelationshipStatus.PENDING and rel.expires_at <= now:
        rel.status = RelationshipStatus.EXPIRED
        rel.save(update_fields=["status", "updated_at"])
        log_relationship_event(
            event="expired", relationship_id=rel.pk, actor_id=None, actor_role="system"
        )
        return True
    return False


def _require_visible_psychologist_user(user):
    if not (user.is_active and user.approval_status == ApprovalStatus.APPROVED):
        raise Http404


def request_psychologist(*, patient_user, psychologist_id):
    patient = PatientProfile.objects.get(user=patient_user)
    if patient.date_of_birth is None:
        raise DomainValidationError({"date_of_birth": [DOB_REQUIRED]})
    psychologist = (
        PsychologistProfile.objects.select_related("user")
        .filter(
            pk=psychologist_id,
            user__role=Role.PSYCHOLOGIST,
            user__is_active=True,
            user__approval_status=ApprovalStatus.APPROVED,
        )
        .first()
    )
    if psychologist is None:
        raise DomainValidationError({"psychologist": [NOT_AVAILABLE]})
    if not psychologist.is_accepting_patients:
        raise DomainValidationError({"psychologist": [NOT_ACCEPTING]})

    now = timezone.now()
    with transaction.atomic():
        stale = CareRelationship.objects.select_for_update(of=("self",)).filter(
            patient=patient, status=RelationshipStatus.PENDING, expires_at__lte=now
        )
        for rel in stale:
            _expire_if_stale(rel, now)
        if CareRelationship.objects.filter(patient=patient, status__in=OPEN_STATUSES).exists():
            raise DomainValidationError({"relationship": [ALREADY_OPEN]})
        recent_decline = (
            CareRelationship.objects.filter(
                patient=patient,
                psychologist=psychologist,
                status=RelationshipStatus.DECLINED,
                cooldown_until__gt=now,
            )
            .order_by("-cooldown_until")
            .first()
        )
        if recent_decline is not None:
            local = timezone.localtime(recent_decline.cooldown_until, ZoneInfo(patient.timezone))
            raise DomainValidationError(
                {"psychologist": [COOLDOWN.format(date=local.date().isoformat())]}
            )
        try:
            with transaction.atomic():
                rel = CareRelationship.objects.create(
                    patient=patient,
                    psychologist=psychologist,
                    status=RelationshipStatus.PENDING,
                    requested_at=now,
                    expires_at=now + REQUEST_EXPIRY,
                )
        except IntegrityError as exc:
            raise DomainValidationError({"relationship": [ALREADY_OPEN]}) from exc
    log_relationship_event(
        event="requested", relationship_id=rel.pk, actor_id=patient_user.pk, actor_role="patient"
    )
    return rel


def _answer(rel_filters, now, apply):
    """Lock the row, expire it if stale, else apply() it if still pending. The
    expiry commits even when the request is rejected afterwards."""
    with transaction.atomic():
        rel = _lock(**rel_filters)
        stale = _expire_if_stale(rel, now)
        if not stale and rel.status == RelationshipStatus.PENDING:
            apply(rel)
            return rel
    raise DomainValidationError({"relationship": [NOT_PENDING]})


def cancel_request(*, patient_user, relationship_id):
    now = timezone.now()

    def apply(rel):
        rel.status = RelationshipStatus.CANCELLED
        rel.save(update_fields=["status", "updated_at"])

    rel = _answer({"pk": relationship_id, "patient__user": patient_user}, now, apply)
    log_relationship_event(
        event="cancelled", relationship_id=rel.pk, actor_id=patient_user.pk, actor_role="patient"
    )
    return rel


def accept_request(*, psychologist_user, relationship_id):
    _require_visible_psychologist_user(psychologist_user)
    now = timezone.now()

    def apply(rel):
        rel.status = RelationshipStatus.ACCEPTED
        rel.responded_at = now
        rel.save(update_fields=["status", "responded_at", "updated_at"])

    rel = _answer({"pk": relationship_id, "psychologist__user": psychologist_user}, now, apply)
    log_relationship_event(
        event="accepted", relationship_id=rel.pk,
        actor_id=psychologist_user.pk, actor_role="psychologist",
    )
    return rel


def decline_request(*, psychologist_user, relationship_id, reason=None):
    _require_visible_psychologist_user(psychologist_user)
    if reason is not None and reason not in DeclineReason.values:
        raise DomainValidationError({"reason": [INVALID_REASON]})
    now = timezone.now()

    def apply(rel):
        rel.status = RelationshipStatus.DECLINED
        rel.responded_at = now
        rel.cooldown_until = now + DECLINE_COOLDOWN
        rel.decline_reason = reason
        rel.save(
            update_fields=["status", "responded_at", "cooldown_until", "decline_reason", "updated_at"]
        )

    rel = _answer({"pk": relationship_id, "psychologist__user": psychologist_user}, now, apply)
    log_relationship_event(
        event="declined", relationship_id=rel.pk, actor_id=psychologist_user.pk,
        actor_role="psychologist", reason=reason,
    )
    return rel
```

Note on the `IntegrityError` test: it patches `CareRelationship.objects.create`; the service calls `CareRelationship.objects.create(...)` exactly as written above.

- [ ] **Step 3: Date-of-birth rule**

In `apps/patients/services.py`, add a module constant after `MAX_PSEUDONYM_ATTEMPTS`:

```python
DOB_CANNOT_CLEAR = "Your date of birth can't be removed once set."
```

and in `update_patient_profile`, directly before the existing `if fields.get("date_of_birth") is not None:` validation, insert:

```python
    if (
        "date_of_birth" in fields
        and not fields["date_of_birth"]
        and profile.date_of_birth is not None
    ):
        # Phase 3: required to request a psychologist, so never removable once set.
        raise DomainValidationError({"date_of_birth": [DOB_CANNOT_CLEAR]})
```

Run: `venv/Scripts/python -m pytest apps/relationships apps/patients -q` → PASS; then the full suite → all pass.

- [ ] **Step 4: Module-reference + commit**

Rows in `### apps/relationships`:

```markdown
| `apps/relationships/services.py` | `request_psychologist()` | Date of birth required; generic "isn't available" for unapproved/inactive/unknown psychologists; accepting check; stale pending expired in the same transaction; one open row; 30-day decline cooldown | `POST /api/v1/relationships/requests/` | MindCare App |
| `apps/relationships/services.py` | `cancel_request()`, `accept_request()`, `decline_request()` | Row-locked, ownership-checked (404), expiry-aware state changes; decline sets the 30-day cooldown | `POST /api/v1/relationships/requests/<id>/{cancel,accept,decline}/` | MindCare App, MindCare Web |
```

and update the `update_patient_profile()` row under `### apps/patients`: "date of birth can be corrected but never cleared once set (Phase 3)".

```bash
git add apps/relationships/services.py apps/relationships/tests/test_services_requests.py apps/relationships/tests/test_races.py apps/patients/services.py apps/patients/tests/test_services.py docs/module-reference.md
git commit -m "feat(relationships): request, cancel, accept, decline with row locks and expiry; DOB can't be cleared

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Ending relationships, unavailable accounts, availability switch, admin hook

**Files:**
- Modify: `apps/relationships/services.py`, `apps/relationships/tests/test_races.py`, `apps/accounts/admin.py`, `docs/module-reference.md`
- Create: `apps/relationships/tests/test_services_ending.py`, `apps/accounts/tests/test_admin_relationships.py`

**Interfaces:**
- Consumes: Task 3 helpers (`_lock`, `_require_visible_psychologist_user`, `INVALID_REASON`), Task 2 selectors.
- Produces (in `apps.relationships.services`): constants `NO_PSYCHOLOGIST`, `REASON_REQUIRED`, `CONFIRM_REQUIRED`, `ACCEPTING_REASON_REQUIRED`, `NOT_ACTIVE`; `end_relationship(*, relationship, ended_by, reason, actor_id=None) -> CareRelationship`; `patient_end_relationship(*, patient_user, confirm) -> CareRelationship`; `psychologist_end_relationship(*, psychologist_user, relationship_id, reason) -> CareRelationship`; `end_for_unavailable_account(*, user) -> None`; `set_accepting_status(*, psychologist_user, accepting, reason=None) -> PsychologistProfile`.

- [ ] **Step 1: Failing tests**

`apps/relationships/tests/test_services_ending.py`:

```python
"""Service tests: ending, unavailable accounts, pause, availability."""

from django.http import Http404
from django.test import TestCase

from apps.accounts.models import ApprovalStatus
from apps.relationships import selectors, services
from apps.relationships.models import RelationshipStatus
from core.exceptions import DomainValidationError
from core.testing import make_patient, make_psychologist


def _accepted(patient, psych):
    rel = services.request_psychologist(patient_user=patient.user, psychologist_id=psych.pk)
    return services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)


class EndRelationshipTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()
        self.rel = _accepted(self.patient, self.psych)

    def test_patient_ends_with_confirm(self):
        rel = services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        self.assertEqual(
            (rel.status, rel.ended_by, rel.end_reason),
            (RelationshipStatus.ENDED, "patient", "patient_ended"),
        )
        self.assertIsNotNone(rel.ended_at)

    def test_patient_must_confirm_with_true(self):
        for value in (False, None, "true", 1):
            with self.subTest(value=value), self.assertRaises(DomainValidationError) as ctx:
                services.patient_end_relationship(patient_user=self.patient.user, confirm=value)
            self.assertEqual(
                ctx.exception.errors,
                {"confirm": ["Confirm that you want to end this relationship."]},
            )

    def test_patient_without_psychologist(self):
        with self.assertRaises(DomainValidationError) as ctx:
            services.patient_end_relationship(patient_user=make_patient().user, confirm=True)
        self.assertEqual(ctx.exception.errors, {"relationship": ["You don't have a psychologist right now."]})

    def test_psychologist_end_requires_reason_from_their_list(self):
        with self.assertRaises(DomainValidationError) as ctx:
            services.psychologist_end_relationship(
                psychologist_user=self.psych.user, relationship_id=self.rel.pk, reason=None
            )
        self.assertEqual(ctx.exception.errors, {"reason": ["Choose a reason."]})
        for bad in ("patient_unresponsive", "patient_ended", "subscription_lapsed"):
            with self.subTest(reason=bad), self.assertRaises(DomainValidationError):
                services.psychologist_end_relationship(
                    psychologist_user=self.psych.user, relationship_id=self.rel.pk, reason=bad
                )
        rel = services.psychologist_end_relationship(
            psychologist_user=self.psych.user, relationship_id=self.rel.pk,
            reason="treatment_completed",
        )
        self.assertEqual((rel.ended_by, rel.end_reason), ("psychologist", "treatment_completed"))

    def test_other_psychologist_gets_404(self):
        with self.assertRaises(Http404):
            services.psychologist_end_relationship(
                psychologist_user=make_psychologist().user, relationship_id=self.rel.pk,
                reason="other",
            )

    def test_subscription_lapsed_is_system_only(self):
        with self.assertRaises(DomainValidationError):
            services.end_relationship(relationship=self.rel, ended_by="patient", reason="subscription_lapsed")
        rel = services.end_relationship(relationship=self.rel, ended_by="system", reason="subscription_lapsed")
        self.assertEqual(rel.end_reason, "subscription_lapsed")

    def test_ending_twice_is_rejected(self):
        services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        with self.assertRaises(DomainValidationError):
            services.end_relationship(relationship=self.rel, ended_by="system", reason="account_unavailable")

    def test_no_cooldown_after_psychologist_ends(self):
        services.psychologist_end_relationship(
            psychologist_user=self.psych.user, relationship_id=self.rel.pk, reason="other"
        )
        again = services.request_psychologist(patient_user=self.patient.user, psychologist_id=self.psych.pk)
        self.assertEqual(again.status, RelationshipStatus.PENDING)


class UnavailableAccountTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()
        self.rel = _accepted(self.patient, self.psych)
        self.other_patient = make_patient()
        self.pending = services.request_psychologist(
            patient_user=self.other_patient.user, psychologist_id=make_psychologist().pk
        )

    def test_deactivation_ends_accepted_rows(self):
        self.psych.user.is_active = False
        self.psych.user.save()
        services.end_for_unavailable_account(user=self.psych.user)
        self.rel.refresh_from_db()
        self.assertEqual(
            (self.rel.status, self.rel.ended_by, self.rel.end_reason),
            ("ended", "system", "account_unavailable"),
        )

    def test_rejection_of_patient_expires_their_pending_request(self):
        services.end_for_unavailable_account(user=self.other_patient.user)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, RelationshipStatus.EXPIRED)

    def test_becoming_pending_is_a_pause_not_an_end(self):
        user = self.psych.user
        user.approval_status = ApprovalStatus.PENDING
        user.save()  # no end_for_unavailable_account call for pending
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
        self.assertFalse(selectors.is_assigned_psychologist(viewer=user, patient_profile=self.patient))
        self.assertIsNone(selectors.get_active_relationship(patient=self.patient))
        rel = services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        self.assertEqual(rel.status, RelationshipStatus.ENDED)


class AvailabilityTests(TestCase):
    def setUp(self):
        self.psych = make_psychologist()

    def test_reason_required_when_off_and_cleared_when_on(self):
        with self.assertRaises(DomainValidationError) as ctx:
            services.set_accepting_status(psychologist_user=self.psych.user, accepting=False)
        self.assertEqual(
            ctx.exception.errors,
            {"reason": ["Choose a reason when you're not accepting new patients."]},
        )
        profile = services.set_accepting_status(
            psychologist_user=self.psych.user, accepting=False, reason="fully_booked"
        )
        self.assertEqual((profile.is_accepting_patients, profile.not_accepting_reason), (False, "fully_booked"))
        profile = services.set_accepting_status(psychologist_user=self.psych.user, accepting=True, reason="away")
        self.assertEqual((profile.is_accepting_patients, profile.not_accepting_reason), (True, None))

    def test_unknown_reason_rejected(self):
        with self.assertRaises(DomainValidationError):
            services.set_accepting_status(psychologist_user=self.psych.user, accepting=False, reason="sick")
```

Append to `apps/relationships/tests/test_races.py`:

```python


class PatientEndVsPsychologistEndRaceTests(TransactionTestCase):
    def test_exactly_one_ends_it(self):
        patient = make_patient()
        psych = make_psychologist()
        rel = services.request_psychologist(patient_user=patient.user, psychologist_id=psych.pk)
        services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)
        results = _run_concurrently(
            lambda: services.patient_end_relationship(patient_user=patient.user, confirm=True),
            lambda: services.psychologist_end_relationship(
                psychologist_user=psych.user, relationship_id=rel.pk, reason="other"
            ),
        )
        self.assertEqual(sorted(results), ["ok", "rejected"])
        rel.refresh_from_db()
        self.assertEqual(rel.status, RelationshipStatus.ENDED)
```

`apps/accounts/tests/test_admin_relationships.py`:

```python
"""Deactivating or rejecting a user in Django admin ends their relationships."""

from django.test import TestCase

from apps.accounts.models import ApprovalStatus, User
from apps.relationships import services
from apps.relationships.models import RelationshipStatus
from core.testing import admin_change_form_data, make_patient, make_psychologist


class UserAdminEndsRelationshipsTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(email="root@example.com", password="strongpass123")
        self.client.force_login(self.root)
        self.patient = make_patient()
        self.psych = make_psychologist()
        rel = services.request_psychologist(patient_user=self.patient.user, psychologist_id=self.psych.pk)
        self.rel = services.accept_request(psychologist_user=self.psych.user, relationship_id=rel.pk)
        self.url = f"/admin/accounts/user/{self.psych.user.pk}/change/"

    def _post(self, **changes):
        data = admin_change_form_data(self.client.get(self.url))
        data.update(changes)
        if changes.get("is_active") is False:
            data.pop("is_active", None)
        return self.client.post(self.url, data)

    def test_deactivating_ends_relationship(self):
        self.assertEqual(self._post(is_active=False).status_code, 302)
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ENDED)

    def test_rejecting_ends_relationship(self):
        self.assertEqual(self._post(approval_status=ApprovalStatus.REJECTED).status_code, 302)
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ENDED)

    def test_moving_to_pending_only_pauses(self):
        self.assertEqual(self._post(approval_status=ApprovalStatus.PENDING).status_code, 302)
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
```

(`core.testing.admin_change_form_data(response)` already exists from Phase 2; it returns the change form's current values as POST data.)

Run: `venv/Scripts/python -m pytest apps/relationships apps/accounts/tests/test_admin_relationships.py -q` → FAIL.

- [ ] **Step 2: Implement**

Append to `apps/relationships/services.py` (and extend the imports: `from apps.relationships.models import EndedBy, EndReason, PATIENT_END_REASONS, PSYCHOLOGIST_END_REASONS, SYSTEM_END_REASONS`; `from apps.psychologists.models import NotAcceptingReason`; `from django.db.models import Q`):

```python
NO_PSYCHOLOGIST = "You don't have a psychologist right now."
REASON_REQUIRED = "Choose a reason."
CONFIRM_REQUIRED = "Confirm that you want to end this relationship."
ACCEPTING_REASON_REQUIRED = "Choose a reason when you're not accepting new patients."
NOT_ACTIVE = "This relationship isn't active."

_ALLOWED_END_REASONS = {
    EndedBy.PATIENT: PATIENT_END_REASONS,
    EndedBy.PSYCHOLOGIST: PSYCHOLOGIST_END_REASONS,
    EndedBy.SYSTEM: SYSTEM_END_REASONS,
}


def end_relationship(*, relationship, ended_by, reason, actor_id=None):
    """The ONLY way an accepted relationship ends (Phase 9 calls this with
    ended_by="system", reason="subscription_lapsed")."""
    if reason not in _ALLOWED_END_REASONS.get(ended_by, ()):
        raise DomainValidationError({"reason": [INVALID_REASON]})
    with transaction.atomic():
        rel = _lock(pk=relationship.pk)
        if rel.status != RelationshipStatus.ACCEPTED:
            raise DomainValidationError({"relationship": [NOT_ACTIVE]})
        rel.status = RelationshipStatus.ENDED
        rel.ended_at = timezone.now()
        rel.ended_by = ended_by
        rel.end_reason = reason
        rel.save(update_fields=["status", "ended_at", "ended_by", "end_reason", "updated_at"])
    log_relationship_event(
        event="ended", relationship_id=rel.pk, actor_id=actor_id,
        actor_role=ended_by, reason=reason,
    )
    return rel


def patient_end_relationship(*, patient_user, confirm):
    if confirm is not True:
        raise DomainValidationError({"confirm": [CONFIRM_REQUIRED]})
    rel = CareRelationship.objects.filter(
        patient__user=patient_user, status=RelationshipStatus.ACCEPTED
    ).first()
    if rel is None:
        raise DomainValidationError({"relationship": [NO_PSYCHOLOGIST]})
    try:
        return end_relationship(
            relationship=rel, ended_by=EndedBy.PATIENT,
            reason=EndReason.PATIENT_ENDED, actor_id=patient_user.pk,
        )
    except DomainValidationError as exc:
        if "relationship" in exc.errors:  # ended concurrently
            raise DomainValidationError({"relationship": [NO_PSYCHOLOGIST]}) from exc
        raise


def psychologist_end_relationship(*, psychologist_user, relationship_id, reason):
    _require_visible_psychologist_user(psychologist_user)
    if not reason:
        raise DomainValidationError({"reason": [REASON_REQUIRED]})
    if reason not in PSYCHOLOGIST_END_REASONS:
        raise DomainValidationError({"reason": [INVALID_REASON]})
    rel = CareRelationship.objects.filter(
        pk=relationship_id, psychologist__user=psychologist_user,
        status=RelationshipStatus.ACCEPTED,
    ).first()
    if rel is None:
        raise Http404
    return end_relationship(
        relationship=rel, ended_by=EndedBy.PSYCHOLOGIST,
        reason=reason, actor_id=psychologist_user.pk,
    )


def end_for_unavailable_account(*, user):
    """Called when a user is DEACTIVATED or REJECTED (never when a psychologist
    becomes pending: that is a pause)."""
    now = timezone.now()
    with transaction.atomic():
        rows = list(
            CareRelationship.objects.select_for_update(of=("self",)).filter(
                Q(patient__user=user) | Q(psychologist__user=user),
                status__in=OPEN_STATUSES,
            )
        )
        for rel in rows:
            if rel.status == RelationshipStatus.ACCEPTED:
                end_relationship(
                    relationship=rel, ended_by=EndedBy.SYSTEM,
                    reason=EndReason.ACCOUNT_UNAVAILABLE,
                )
            else:
                rel.status = RelationshipStatus.EXPIRED
                rel.save(update_fields=["status", "updated_at"])
                log_relationship_event(
                    event="expired", relationship_id=rel.pk, actor_id=None, actor_role="system"
                )
    return None


def set_accepting_status(*, psychologist_user, accepting, reason=None):
    profile = PsychologistProfile.objects.get(user=psychologist_user)
    if accepting:
        profile.is_accepting_patients = True
        profile.not_accepting_reason = None
    else:
        if not reason:
            raise DomainValidationError({"reason": [ACCEPTING_REASON_REQUIRED]})
        if reason not in NotAcceptingReason.values:
            raise DomainValidationError({"reason": [INVALID_REASON]})
        profile.is_accepting_patients = False
        profile.not_accepting_reason = reason
    profile.save(update_fields=["is_accepting_patients", "not_accepting_reason", "updated_at"])
    return profile
```

In `apps/accounts/admin.py`, add `from apps.accounts.models import ApprovalStatus, User` (replace the existing import) and inside `UserAdmin`:

```python
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and {"is_active", "approval_status"} & set(form.changed_data):
            if not obj.is_active or obj.approval_status == ApprovalStatus.REJECTED:
                # Deactivated or rejected: end their relationships. Becoming
                # pending (re-review) is a pause and ends nothing.
                from apps.relationships.services import end_for_unavailable_account

                end_for_unavailable_account(user=obj)
```

Add one line to the module docstring: "Deactivating or rejecting a user here ends their care relationships (moving a psychologist back to pending only pauses them)."

Run: `venv/Scripts/python -m pytest apps/relationships apps/accounts -q` → PASS; full suite → all pass.

- [ ] **Step 3: Module-reference + commit**

```markdown
| `apps/relationships/services.py` | `end_relationship()` | The only way an accepted relationship ends; reason validated per `ended_by` (`subscription_lapsed` system-only, reserved for Phase 9); row-locked | — (called by the views below and by Phase 9) | neither (internal) |
| `apps/relationships/services.py` | `patient_end_relationship()` | Patient ends their psychologist; `confirm` must be JSON `true` | `POST /api/v1/relationships/current/end/` | MindCare App |
| `apps/relationships/services.py` | `psychologist_end_relationship()` | Psychologist ends with a required reason (`treatment_completed`, `referred_elsewhere`, `other`) | `POST /api/v1/relationships/patients/<id>/end/` | MindCare Web |
| `apps/relationships/services.py` | `end_for_unavailable_account()` | On deactivation or rejection: accepted rows end (system/account_unavailable), pending rows expire; not on pending (pause) | — (called from `UserAdmin.save_model`) | neither (internal) |
| `apps/relationships/services.py` | `set_accepting_status()` | Accepting switch; reason required when off, cleared when on | `PUT /api/v1/psychologists/me/availability/` | MindCare Web |
```

and update the `UserAdmin` row: "deactivating/rejecting ends care relationships".

```bash
git add apps/relationships/services.py apps/relationships/tests/test_services_ending.py apps/relationships/tests/test_races.py apps/accounts/admin.py apps/accounts/tests/test_admin_relationships.py docs/module-reference.md
git commit -m "feat(relationships): end relationships, unavailable-account handling, availability switch, admin hook

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Psychologist activity tracking

**Files:**
- Modify: `apps/relationships/services.py`, `config/settings/base.py`, `docs/module-reference.md`
- Create: `apps/accounts/authentication.py`, `apps/relationships/tests/test_activity.py`

**Interfaces:**
- Consumes: `User.last_active_at` (Task 1).
- Produces: `apps.relationships.services.record_activity(*, user) -> None`, `ACTIVITY_CACHE_SECONDS = 15 * 60`; `apps.accounts.authentication.ActivityTrackingJWTAuthentication` (DRF default authentication class).

- [ ] **Step 1: Failing tests**

`apps/relationships/tests/test_activity.py`:

```python
"""Activity tracking: psychologists only, cached, never breaks auth."""

from unittest.mock import patch

from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User
from apps.relationships.services import record_activity
from core.testing import make_patient, make_psychologist


class RecordActivityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()

    def test_psychologist_written_once_per_window(self):
        record_activity(user=self.psych.user)
        first = User.objects.get(pk=self.psych.user.pk).last_active_at
        self.assertIsNotNone(first)
        with patch.object(User.objects, "filter", wraps=User.objects.filter) as spy:
            record_activity(user=self.psych.user)
        spy.assert_not_called()  # cache hit: no database write

    def test_other_roles_never_written(self):
        patient = make_patient()
        with patch("apps.relationships.services.cache") as fake_cache:
            record_activity(user=patient.user)
        fake_cache.get.assert_not_called()
        self.assertIsNone(User.objects.get(pk=patient.user.pk).last_active_at)

    def test_cache_error_skips_silently(self):
        with patch("apps.relationships.services.cache") as fake_cache:
            fake_cache.get.side_effect = ConnectionError("redis down")
            record_activity(user=self.psych.user)  # no exception
        self.assertIsNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def _auth(self, user):
        token = RefreshToken.for_user(user)
        token["role"] = user.role
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return token

    def test_authenticated_request_records_activity(self):
        self._auth(self.psych.user)
        self.client.get("/api/v1/psychologists/me/")
        self.assertIsNotNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def test_logout_does_not_record_activity(self):
        refresh = self._auth(self.psych.user)
        self.client.post("/api/v1/accounts/logout/", {"refresh": str(refresh)}, format="json")
        self.assertIsNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def test_redis_outage_never_breaks_authentication(self):
        self._auth(self.psych.user)
        with patch("apps.relationships.services.cache") as fake_cache:
            fake_cache.get.side_effect = ConnectionError("redis down")
            response = self.client.get("/api/v1/psychologists/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.psych.user.role, Role.PSYCHOLOGIST)
```

Run: `venv/Scripts/python -m pytest apps/relationships/tests/test_activity.py -q` → FAIL.

- [ ] **Step 2: Implement**

Append to `apps/relationships/services.py` (imports: `from django.core.cache import cache`; `from apps.accounts.models import User`):

```python
ACTIVITY_CACHE_SECONDS = 15 * 60


def record_activity(*, user):
    """Psychologists only. At most one write per 15 minutes; a cache outage skips
    the update and never breaks authentication."""
    if getattr(user, "role", None) != Role.PSYCHOLOGIST:
        return None
    key = f"last_active:{user.pk}"
    try:
        if cache.get(key):
            return None
        cache.set(key, 1, ACTIVITY_CACHE_SECONDS)
    except Exception:  # any cache failure must not affect authentication
        return None
    User.objects.filter(pk=user.pk).update(last_active_at=timezone.now())
    return None
```

`apps/accounts/authentication.py`:

```python
"""DRF authentication that records psychologist activity (Phase 3)."""

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.relationships.services import record_activity

# Token housekeeping isn't "activity".
UNTRACKED_PATHS = frozenset({"/api/v1/accounts/refresh/", "/api/v1/accounts/logout/"})


class ActivityTrackingJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None and request.path not in UNTRACKED_PATHS:
            record_activity(user=result[0])
        return result
```

In `config/settings/base.py`, change `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` to:

```python
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.ActivityTrackingJWTAuthentication",
    ),
```

Run: `venv/Scripts/python -m pytest apps/relationships/tests/test_activity.py -q` → PASS; full suite → all pass (existing JWT tests are unaffected).

- [ ] **Step 3: Module-reference + commit**

```markdown
| `apps/relationships/services.py` | `record_activity()` | Psychologist `last_active_at`, at most every 15 min via cache key; cache errors skip silently | — | neither (internal) |
| `apps/accounts/authentication.py` | `ActivityTrackingJWTAuthentication` | DRF default auth: simplejwt + `record_activity()`, except on refresh/logout | all authenticated endpoints | MindCare Web, MindCare App |
```

```bash
git add apps/relationships/services.py apps/relationships/tests/test_activity.py apps/accounts/authentication.py config/settings/base.py docs/module-reference.md
git commit -m "feat(relationships): psychologist activity tracking in the JWT auth layer

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Directory selectors and `people_in_care`

**Files:**
- Modify: `apps/psychologists/selectors.py`, `apps/stats/selectors.py`, `apps/stats/tests/test_selectors.py`, `docs/module-reference.md`
- Create: `apps/psychologists/tests/test_directory.py`

**Interfaces:**
- Consumes: Task 1 fields, factories; `apps.relationships.models`.
- Produces: `apps.psychologists.selectors.visible_psychologists()`, `list_directory(*, specialization=None, language=None, gender=None, country=None, city=None, accepting=None, search=None)`, `get_directory_entry(*, profile_id) -> PsychologistProfile | None`.

- [ ] **Step 1: Failing tests**

`apps/psychologists/tests/test_directory.py`:

```python
"""Directory selectors: visibility, filters, ordering."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, User
from apps.psychologists.selectors import get_directory_entry, list_directory
from apps.reference.models import Language, Specialization
from core.testing import make_psychologist


class DirectoryTests(TestCase):
    def setUp(self):
        self.visible = make_psychologist(full_name="Dr Aamir")
        self.pending = make_psychologist(approval_status=ApprovalStatus.PENDING)
        self.inactive = make_psychologist(is_active=False)

    def test_only_approved_active(self):
        ids = {p.pk for p in list_directory()}
        self.assertIn(self.visible.pk, ids)
        self.assertNotIn(self.pending.pk, ids)
        self.assertNotIn(self.inactive.pk, ids)
        self.assertIsNone(get_directory_entry(profile_id=self.pending.pk))
        self.assertEqual(get_directory_entry(profile_id=self.visible.pk), self.visible)

    def test_filters(self):
        other = make_psychologist(
            specializations=list(Specialization.objects.filter(slug="grief")),
            languages=list(Language.objects.filter(code="en")),
            gender="female", city="Karachi",
        )
        self.assertEqual([p.pk for p in list_directory(specialization="grief")], [other.pk])
        self.assertNotIn(other.pk, [p.pk for p in list_directory(language="ur")])
        self.assertEqual([p.pk for p in list_directory(gender="female")], [other.pk])
        self.assertEqual([p.pk for p in list_directory(city=other.city_id)], [other.pk])
        self.assertIn(other.pk, [p.pk for p in list_directory(country="PK")])
        self.assertEqual([p.pk for p in list_directory(search="aamir")], [self.visible.pk])

    def test_accepting_filter_and_ordering(self):
        busy = make_psychologist()
        busy.is_accepting_patients = False
        busy.not_accepting_reason = "fully_booked"
        busy.save()
        recent = make_psychologist()
        User.objects.filter(pk=recent.user_id).update(last_active_at=timezone.now())
        older = make_psychologist()
        User.objects.filter(pk=older.user_id).update(last_active_at=timezone.now() - timedelta(days=3))
        ordered = [p.pk for p in list_directory()]
        self.assertLess(ordered.index(recent.pk), ordered.index(older.pk))
        self.assertLess(ordered.index(older.pk), ordered.index(busy.pk))  # accepting first
        self.assertNotIn(busy.pk, [p.pk for p in list_directory(accepting=True)])
        self.assertEqual([p.pk for p in list_directory(accepting=False)], [busy.pk])
```

Append to `apps/stats/tests/test_selectors.py` (keep existing tests; update the existing `people_in_care` expectation as described below):

```python


class PeopleInCareTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_counts_patients_with_accepted_relationship_to_visible_psychologist(self):
        from apps.relationships import services
        from core.testing import make_patient, make_psychologist

        psych = make_psychologist()
        in_care = make_patient()
        rel = services.request_psychologist(patient_user=in_care.user, psychologist_id=psych.pk)
        services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)
        make_patient()  # registered, no psychologist
        waiting = make_patient()
        services.request_psychologist(patient_user=waiting.user, psychologist_id=make_psychologist().pk)
        self.assertEqual(get_public_platform_stats()["people_in_care"], 1)

        psych.user.approval_status = "pending"  # paused: not counted
        psych.user.save()
        cache.clear()
        self.assertEqual(get_public_platform_stats()["people_in_care"], 0)

    def test_reflects_new_relationships_once_cache_cleared(self):
        from apps.relationships import services
        from core.testing import make_patient, make_psychologist

        self.assertEqual(get_public_platform_stats()["people_in_care"], 0)
        psych, patient = make_psychologist(), make_patient()
        rel = services.request_psychologist(patient_user=patient.user, psychologist_id=psych.pk)
        services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)
        self.assertEqual(get_public_platform_stats()["people_in_care"], 0)  # cached
        cache.clear()
        self.assertEqual(get_public_platform_stats()["people_in_care"], 1)
```

The existing `PublicStatsTests.test_counts` (line ~55) and `test_result_is_cached` (line ~66) both assert `people_in_care == 2` for active patients with no relationships. Change both expectations to `0` (comment: "patients with an accepted relationship; none here"). Caching itself is now proven by `test_reflects_new_relationships_once_cache_cleared` above. Leave the `verified_therapists` and `cities` assertions unchanged.

Run: `venv/Scripts/python -m pytest apps/psychologists/tests/test_directory.py apps/stats -q` → FAIL.

- [ ] **Step 2: Implement**

Append to `apps/psychologists/selectors.py` (imports: `from django.db.models import F`; `from apps.accounts.models import ApprovalStatus, Role`):

```python
def visible_psychologists():
    """Approved, active psychologists: the only ones patients can see or request."""
    return (
        PsychologistProfile.objects.filter(
            user__role=Role.PSYCHOLOGIST,
            user__is_active=True,
            user__approval_status=ApprovalStatus.APPROVED,
        )
        .select_related("user", "country", "city__country", "license_issuing_country")
        .prefetch_related("specializations", "languages")
    )


def list_directory(
    *, specialization=None, language=None, gender=None, country=None,
    city=None, accepting=None, search=None,
):
    qs = visible_psychologists()
    if specialization:
        qs = qs.filter(specializations__slug=specialization)
    if language:
        qs = qs.filter(languages__code=language)
    if gender:
        qs = qs.filter(gender=gender)
    if country:
        qs = qs.filter(country__code=country.upper())
    if city:
        qs = qs.filter(city_id=city)
    if accepting is not None:
        qs = qs.filter(is_accepting_patients=accepting)
    if search:
        qs = qs.filter(user__full_name__icontains=search.strip())
    return qs.order_by(
        F("is_accepting_patients").desc(),
        F("user__last_active_at").desc(nulls_last=True),
        "user__full_name",
        "pk",
    )


def get_directory_entry(*, profile_id):
    return visible_psychologists().filter(pk=profile_id).first()
```

In `apps/stats/selectors.py`, add `from apps.relationships.models import CareRelationship, RelationshipStatus` and replace the `people_in_care` lines (the TEMPORARY comment and the count) with:

```python
    # Patients in active care: an accepted relationship to an approved, active
    # psychologist (docs/decisions.md, 2026-10-06). A paused psychologist's
    # patients aren't counted.
    people_in_care = (
        CareRelationship.objects.filter(
            status=RelationshipStatus.ACCEPTED,
            patient__user__is_active=True,
            psychologist__user__is_active=True,
            psychologist__user__approval_status=ApprovalStatus.APPROVED,
        )
        .values("patient_id")
        .distinct()
        .count()
    )
```

Run: `venv/Scripts/python -m pytest apps/psychologists apps/stats -q` → PASS; full suite → all pass.

- [ ] **Step 3: Module-reference + commit**

Under `### apps/psychologists`: `| \`apps/psychologists/selectors.py\` | \`visible_psychologists()\`, \`list_directory()\`, \`get_directory_entry()\` | Approved, active psychologists only; filters (specialization, language, gender, country, city, accepting, name search) combined with AND; accepting first, then most recently active | \`GET /api/v1/psychologists/directory/\` | MindCare App |`. Update the `### apps/stats` `get_public_platform_stats()` row: "`people_in_care` = patients with an accepted relationship to an approved, active psychologist (Phase 3; no longer temporary)".

```bash
git add apps/psychologists/selectors.py apps/psychologists/tests/test_directory.py apps/stats/selectors.py apps/stats/tests/test_selectors.py docs/module-reference.md
git commit -m "feat(psychologists,stats): directory selectors; people_in_care from accepted relationships

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Patient-facing API (directory, requests, current, end, recent)

**Files:**
- Modify: `core/pagination.py`, `apps/psychologists/api/serializers.py`, `apps/psychologists/api/views.py`, `apps/psychologists/api/urls.py`, `apps/relationships/api/serializers.py`, `apps/relationships/api/views.py`, `apps/relationships/api/urls.py`, `config/settings/base.py` (throttle rates), `docs/module-reference.md`
- Create: `apps/relationships/tests/test_api_patient.py`

**Interfaces:**
- Consumes: Tasks 2–6 services/selectors; `core.serializers.StrictTrueField`; reference serializers.
- Produces: `core.pagination.StandardPagination`; `apps.psychologists.api.serializers.DirectoryCardSerializer`, `MinimalCardSerializer`, `DIRECTORY_CARD_FIELDS`; `apps.relationships.api.serializers.RelationshipPatientViewSerializer`; throttle classes `DirectoryRateThrottle` (scope `directory`), `RelationshipRequestRateThrottle` (scope `relationship_requests`).

- [ ] **Step 1: Failing API tests**

`apps/relationships/tests/test_api_patient.py`:

```python
"""Patient-facing relationship API."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import ApprovalStatus
from apps.psychologists.api.serializers import DIRECTORY_CARD_FIELDS
from apps.relationships import services
from core.testing import make_patient, make_psychologist

DIRECTORY = "/api/v1/psychologists/directory/"
REQUESTS = "/api/v1/relationships/requests/"
CURRENT = "/api/v1/relationships/current/"
END = "/api/v1/relationships/current/end/"
RECENT = "/api/v1/relationships/recent/"


class PatientAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.patient = make_patient()
        self.psych = make_psychologist(full_name="Dr Sana")
        self.client.force_authenticate(self.patient.user)

    def test_directory_card_has_exact_keys(self):
        r = self.client.get(DIRECTORY)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        card = r.data["results"][0]
        self.assertEqual(set(card), set(DIRECTORY_CARD_FIELDS))
        for forbidden in ("license_number", "last_active_at", "not_accepting_reason", "email", "approval_status"):
            self.assertNotIn(forbidden, card)
        self.assertEqual(card["last_active"], "never")

    def test_directory_page_size_capped_at_50(self):
        r = self.client.get(DIRECTORY, {"page_size": 500})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(r.data["results"]), 50)

    def test_directory_patients_only(self):
        self.client.force_authenticate(self.psych.user)
        self.assertEqual(self.client.get(DIRECTORY).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(DIRECTORY).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_directory_detail_404_for_unapproved(self):
        hidden = make_psychologist(approval_status=ApprovalStatus.PENDING)
        self.assertEqual(self.client.get(f"{DIRECTORY}{hidden.pk}/").status_code, status.HTTP_404_NOT_FOUND)

    def test_request_then_current_shows_card_and_expiry(self):
        r = self.client.post(REQUESTS, {"psychologist": self.psych.pk}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        current = self.client.get(CURRENT).data["relationship"]
        self.assertEqual(current["status"], "pending")
        self.assertIn("expires_at", current)
        self.assertEqual(current["psychologist"]["last_active"], "never")

    def test_request_without_dob_returns_exact_error(self):
        patient = make_patient(date_of_birth=False)
        self.client.force_authenticate(patient.user)
        r = self.client.post(REQUESTS, {"psychologist": self.psych.pk}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            r.data,
            {"date_of_birth": ["Add your date of birth to your profile before requesting a psychologist."]},
        )

    def test_current_empty(self):
        self.assertEqual(self.client.get(CURRENT).data, {"relationship": None})

    def test_cancel_and_other_patients_404(self):
        rel_id = self.client.post(REQUESTS, {"psychologist": self.psych.pk}, format="json").data["id"]
        self.client.force_authenticate(make_patient().user)
        self.assertEqual(
            self.client.post(f"{REQUESTS}{rel_id}/cancel/").status_code, status.HTTP_404_NOT_FOUND
        )
        self.client.force_authenticate(self.patient.user)
        self.assertEqual(self.client.post(f"{REQUESTS}{rel_id}/cancel/").data["status"], "cancelled")

    def test_end_requires_strict_true(self):
        rel = services.request_psychologist(patient_user=self.patient.user, psychologist_id=self.psych.pk)
        services.accept_request(psychologist_user=self.psych.user, relationship_id=rel.pk)
        for value in ("true", 1, False, None):
            with self.subTest(value=value):
                r = self.client.post(END, {"confirm": value}, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(r.data, {"confirm": ["Confirm that you want to end this relationship."]})
        r = self.client.post(END, {"confirm": True}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], "ended")

    def test_minimal_card_when_psychologist_not_visible(self):
        rel = services.request_psychologist(patient_user=self.patient.user, psychologist_id=self.psych.pk)
        services.accept_request(psychologist_user=self.psych.user, relationship_id=rel.pk)
        self.psych.user.approval_status = ApprovalStatus.PENDING  # paused
        self.psych.user.save()
        card = self.client.get(CURRENT).data["relationship"]["psychologist"]
        self.assertEqual(set(card), {"id", "full_name"})
        history_card = self.client.get(REQUESTS).data["results"][0]["psychologist"]
        self.assertEqual(set(history_card), {"id", "full_name"})

    def test_recent_lists_past_psychologist(self):
        rel = services.request_psychologist(patient_user=self.patient.user, psychologist_id=self.psych.pk)
        services.accept_request(psychologist_user=self.psych.user, relationship_id=rel.pk)
        services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        r = self.client.get(RECENT)
        self.assertEqual([c["id"] for c in r.data], [self.psych.pk])

    def test_throttle_scopes(self):
        from apps.psychologists.api.views import DirectoryListView
        from apps.relationships.api.views import RequestListCreateView

        self.assertEqual(DirectoryListView.throttle_classes[0].scope, "directory")
        view = RequestListCreateView()
        view.request = type("R", (), {"method": "POST"})()
        self.assertEqual(view.get_throttles()[0].scope, "relationship_requests")
        view.request = type("R", (), {"method": "GET"})()
        self.assertEqual(view.get_throttles(), [])
```

Run: `venv/Scripts/python -m pytest apps/relationships/tests/test_api_patient.py -q` → FAIL (404s / ImportError).

- [ ] **Step 2: Pagination and throttle settings**

Replace `core/pagination.py` with:

```python
"""Shared DRF pagination: page-number, default 20 per page, at most 50."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50
```

Add to `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` in `config/settings/base.py`: `"directory": "60/min"`, `"relationship_requests": "10/hour"`.

- [ ] **Step 3: Directory serializers and views**

Append to `apps/psychologists/api/serializers.py` (imports: `from drf_spectacular.utils import extend_schema_field`; `from drf_spectacular.types import OpenApiTypes`; `from apps.relationships.selectors import last_active_band`):

```python
DIRECTORY_CARD_FIELDS = [
    "id", "full_name", "gender", "bio", "qualifications",
    "license_issuing_country", "license_issuing_authority", "specializations",
    "languages", "years_of_experience", "country", "city", "timezone",
    "is_accepting_patients", "last_active",
]


class DirectoryCardSerializer(serializers.ModelSerializer):
    """What patients see. Never license_number, last_active_at,
    not_accepting_reason or other admin-only fields."""

    full_name = serializers.CharField(source="user.full_name", read_only=True)
    license_issuing_country = CountrySerializer(read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    country = CountrySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    last_active = serializers.SerializerMethodField()

    class Meta:
        model = PsychologistProfile
        fields = DIRECTORY_CARD_FIELDS
        read_only_fields = DIRECTORY_CARD_FIELDS

    @extend_schema_field(OpenApiTypes.STR)
    def get_last_active(self, obj):
        return last_active_band(obj.user.last_active_at)


class MinimalCardSerializer(serializers.ModelSerializer):
    """Shown when a psychologist is no longer approved and active."""

    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = PsychologistProfile
        fields = ["id", "full_name"]
        read_only_fields = fields


class DirectoryQuerySerializer(serializers.Serializer):
    specialization = serializers.CharField(required=False, max_length=50)
    language = serializers.CharField(required=False, max_length=2)
    gender = serializers.ChoiceField(choices=Gender.choices, required=False)
    country = serializers.CharField(required=False, max_length=2)
    city = serializers.IntegerField(required=False, min_value=1)
    accepting = serializers.BooleanField(required=False, allow_null=True, default=None)
    search = serializers.CharField(required=False, max_length=120)
```

Append to `apps/psychologists/api/views.py` (imports: `from drf_spectacular.utils import OpenApiParameter`; `from rest_framework.exceptions import NotFound`; `from rest_framework.throttling import UserRateThrottle`; `from apps.psychologists.api.serializers import DirectoryCardSerializer, DirectoryQuerySerializer`; `from core.pagination import StandardPagination`; `from core.permissions import IsPatient`):

```python
class DirectoryRateThrottle(UserRateThrottle):
    scope = "directory"


class DirectoryListView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    throttle_classes = [DirectoryRateThrottle]

    @extend_schema(
        parameters=[DirectoryQuerySerializer],
        responses=DirectoryCardSerializer(many=True),
    )
    def get(self, request):
        query = DirectoryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        qs = selectors.list_directory(**query.validated_data)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(DirectoryCardSerializer(page, many=True).data)


class DirectoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    throttle_classes = [DirectoryRateThrottle]

    @extend_schema(responses=DirectoryCardSerializer)
    def get(self, request, pk):
        profile = selectors.get_directory_entry(profile_id=pk)
        if profile is None:
            raise NotFound()
        return Response(DirectoryCardSerializer(profile).data)
```

Add to `apps/psychologists/api/urls.py` `urlpatterns`:

```python
    path("directory/", DirectoryListView.as_view(), name="directory"),
    path("directory/<int:pk>/", DirectoryDetailView.as_view(), name="directory-detail"),
```

(import both views).

- [ ] **Step 4: Relationship serializers (patient side) and views**

`apps/relationships/api/serializers.py` (keep the docstring, then):

```python
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.psychologists.api.serializers import DirectoryCardSerializer, MinimalCardSerializer
from apps.relationships.models import CareRelationship
from apps.relationships.selectors import psychologist_is_visible
from core.serializers import RejectUnknownFieldsMixin, StrictTrueField

CONFIRM_MESSAGE = "Confirm that you want to end this relationship."


class RequestCreateSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    psychologist = serializers.IntegerField(min_value=1)


class PatientEndSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    confirm = StrictTrueField(
        error_messages={"invalid": CONFIRM_MESSAGE, "required": CONFIRM_MESSAGE, "null": CONFIRM_MESSAGE}
    )


class RelationshipPatientViewSerializer(serializers.ModelSerializer):
    psychologist = serializers.SerializerMethodField()

    class Meta:
        model = CareRelationship
        fields = [
            "id", "status", "psychologist", "requested_at", "expires_at",
            "responded_at", "decline_reason", "cooldown_until", "ended_at",
            "ended_by", "end_reason",
        ]
        read_only_fields = fields

    @extend_schema_field(DirectoryCardSerializer)
    def get_psychologist(self, obj):
        if psychologist_is_visible(obj.psychologist):
            return DirectoryCardSerializer(obj.psychologist).data
        return MinimalCardSerializer(obj.psychologist).data
```

`apps/relationships/api/views.py` (keep the docstring, then):

```python
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.psychologists.api.serializers import DirectoryCardSerializer
from apps.relationships import selectors, services
from apps.relationships.api.serializers import (
    PatientEndSerializer,
    RelationshipPatientViewSerializer,
    RequestCreateSerializer,
)
from core.exceptions import DomainValidationError
from core.pagination import StandardPagination
from core.permissions import IsPatient


def _domain(callable_, **kwargs):
    try:
        return callable_(**kwargs)
    except DomainValidationError as exc:
        raise ValidationError(exc.errors, code=exc.code) from exc


class RelationshipRequestRateThrottle(UserRateThrottle):
    scope = "relationship_requests"


class RequestListCreateView(APIView):
    """GET: the patient's request history (the App's history screen).
    POST: send a request. Only POST is throttled."""

    permission_classes = [IsAuthenticated, IsPatient]

    def get_throttles(self):
        if self.request.method == "POST":
            return [RelationshipRequestRateThrottle()]
        return []

    @extend_schema(responses=RelationshipPatientViewSerializer(many=True))
    def get(self, request):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(
            selectors.patient_requests(patient_user=request.user), request, view=self
        )
        return paginator.get_paginated_response(RelationshipPatientViewSerializer(page, many=True).data)

    @extend_schema(request=RequestCreateSerializer, responses={201: RelationshipPatientViewSerializer})
    def post(self, request):
        body = RequestCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        rel = _domain(
            services.request_psychologist,
            patient_user=request.user,
            psychologist_id=body.validated_data["psychologist"],
        )
        return Response(RelationshipPatientViewSerializer(rel).data, status=status.HTTP_201_CREATED)


class CancelRequestView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(request=None, responses=RelationshipPatientViewSerializer)
    def post(self, request, pk):
        rel = _domain(services.cancel_request, patient_user=request.user, relationship_id=pk)
        return Response(RelationshipPatientViewSerializer(rel).data)


class CurrentRelationshipView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(
        responses=inline_serializer(
            "CurrentRelationship",
            {"relationship": RelationshipPatientViewSerializer(allow_null=True)},
        )
    )
    def get(self, request):
        rel = selectors.patient_current(patient_user=request.user)
        data = RelationshipPatientViewSerializer(rel).data if rel else None
        return Response({"relationship": data})


class EndCurrentRelationshipView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(request=PatientEndSerializer, responses=RelationshipPatientViewSerializer)
    def post(self, request):
        body = PatientEndSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        rel = _domain(services.patient_end_relationship, patient_user=request.user, confirm=True)
        return Response(RelationshipPatientViewSerializer(rel).data)


class RecentPsychologistsView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(responses=DirectoryCardSerializer(many=True))
    def get(self, request):
        cards = selectors.recent_psychologists(patient_user=request.user)
        return Response(DirectoryCardSerializer(cards, many=True).data)
```


`apps/relationships/api/urls.py`:

```python
"""URL routes for the relationships API, included under /api/v1/relationships/."""

from django.urls import path

from apps.relationships.api.views import (
    CancelRequestView,
    CurrentRelationshipView,
    EndCurrentRelationshipView,
    RecentPsychologistsView,
    RequestListCreateView,
)

app_name = "relationships"

urlpatterns = [
    path("requests/", RequestListCreateView.as_view(), name="requests"),
    path("requests/<int:pk>/cancel/", CancelRequestView.as_view(), name="request-cancel"),
    path("current/", CurrentRelationshipView.as_view(), name="current"),
    path("current/end/", EndCurrentRelationshipView.as_view(), name="current-end"),
    path("recent/", RecentPsychologistsView.as_view(), name="recent"),
]
```

Run: `venv/Scripts/python -m pytest apps/relationships/tests/test_api_patient.py -q` → PASS; full suite → all pass.

- [ ] **Step 5: Module-reference + commit**

Rows: `DirectoryListView` / `DirectoryDetailView` (`GET /api/v1/psychologists/directory/[<id>/]`, MindCare App); `RequestListCreateView` (`GET`/`POST /api/v1/relationships/requests/` — GET is the App's history screen), `CancelRequestView`, `CurrentRelationshipView`, `EndCurrentRelationshipView`, `RecentPsychologistsView` (MindCare App); `core/pagination.py` `StandardPagination` (20 / max 50).

```bash
git add core/pagination.py apps/psychologists/api/serializers.py apps/psychologists/api/views.py apps/psychologists/api/urls.py apps/relationships/api/serializers.py apps/relationships/api/views.py apps/relationships/api/urls.py apps/relationships/tests/test_api_patient.py config/settings/base.py docs/module-reference.md
git commit -m "feat(relationships): patient API - directory, requests, current, end, recent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Psychologist-facing API (inbox, accept, decline, patients, history, end, availability) and privacy tests

**Files:**
- Modify: `apps/relationships/api/serializers.py`, `apps/relationships/api/views.py`, `apps/relationships/api/urls.py`, `apps/psychologists/api/serializers.py`, `apps/psychologists/api/views.py`, `apps/psychologists/api/urls.py`, `core/tests/test_schema.py`, `docs/module-reference.md`
- Create: `apps/relationships/tests/test_api_psychologist.py`

**Interfaces:**
- Consumes: Tasks 2–7.
- Produces: serializers `InboxItemSerializer`, `AssignedPatientSerializer` (+ `ASSIGNED_PATIENT_FIELDS`), `HistoryItemSerializer`, `DeclineSerializer`, `PsychologistEndSerializer` (relationships); `AvailabilitySerializer` (psychologists); views `InboxView`, `AcceptRequestView`, `DeclineRequestView`, `PatientListView`, `PatientDetailView`, `PatientEndView`, `HistoryView`, `AvailabilityView`.

- [ ] **Step 1: Failing API + privacy tests**

`apps/relationships/tests/test_api_psychologist.py`:

```python
"""Psychologist-facing relationship API, including two-psychologist privacy."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.relationships import services
from apps.relationships.api.serializers import ASSIGNED_PATIENT_FIELDS
from core.testing import make_patient, make_psychologist

BASE = "/api/v1/relationships"
AVAILABILITY = "/api/v1/psychologists/me/availability/"


def _accept(patient, psych):
    rel = services.request_psychologist(patient_user=patient.user, psychologist_id=psych.pk)
    return services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)


class InboxAndAnswerTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.patient = make_patient(full_name="Bilal Hassan")
        self.rel = services.request_psychologist(patient_user=self.patient.user, psychologist_id=self.psych.pk)
        self.client.force_authenticate(self.psych.user)

    def test_inbox_item_shape_no_identity(self):
        item = self.client.get(f"{BASE}/inbox/").data[0]
        self.assertEqual(set(item), {"id", "requested_at", "expires_at", "requester"})
        self.assertEqual(
            set(item["requester"]),
            {"pseudonym", "preferred_language", "timezone", "country", "gender", "age"},
        )
        self.assertNotIn("Bilal Hassan", str(item))

    def test_accept_and_decline(self):
        r = self.client.post(f"{BASE}/requests/{self.rel.pk}/accept/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        other = make_patient()
        rel2 = services.request_psychologist(patient_user=other.user, psychologist_id=self.psych.pk)
        r = self.client.post(f"{BASE}/requests/{rel2.pk}/decline/", {"reason": "other"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_patient_role_forbidden(self):
        self.client.force_authenticate(self.patient.user)
        self.assertEqual(self.client.get(f"{BASE}/inbox/").status_code, status.HTTP_403_FORBIDDEN)


class AssignedPatientTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.patient = make_patient(full_name="Bilal Hassan")
        self.rel = _accept(self.patient, self.psych)
        self.client.force_authenticate(self.psych.user)

    def test_patient_detail_has_age_never_date_of_birth(self):
        data = self.client.get(f"{BASE}/patients/{self.rel.pk}/").data
        self.assertEqual(set(data), set(ASSIGNED_PATIENT_FIELDS))
        self.assertNotIn("date_of_birth", data)
        self.assertEqual(data["full_name"], "Bilal Hassan")
        self.assertIsInstance(data["age"], int)

    def test_end_requires_reason_and_rejects_patient_unresponsive(self):
        url = f"{BASE}/patients/{self.rel.pk}/end/"
        r = self.client.post(url, {}, format="json")
        self.assertEqual(r.data, {"reason": ["Choose a reason."]})
        r = self.client.post(url, {"reason": "patient_unresponsive"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.client.post(url, {"reason": "treatment_completed"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_history_is_pseudonym_only(self):
        services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        item = self.client.get(f"{BASE}/history/").data[0]
        self.assertEqual(
            set(item), {"relationship_id", "pseudonym", "accepted_at", "ended_at", "ended_by", "end_reason"}
        )
        self.assertNotIn("Bilal Hassan", str(item))


class TwoPsychologistPrivacyTests(APITestCase):
    """A and B each have their own patients; neither sees the other's."""

    def setUp(self):
        cache.clear()
        self.a, self.b = make_psychologist(), make_psychologist()
        self.pa = make_patient(full_name="Patient Of A")
        self.pb = make_patient(full_name="Patient Of B")
        self.rel_a = _accept(self.pa, self.a)
        self.rel_b = _accept(self.pb, self.b)

    def test_each_sees_only_their_own(self):
        self.client.force_authenticate(self.a.user)
        names = [p["full_name"] for p in self.client.get(f"{BASE}/patients/").data]
        self.assertEqual(names, ["Patient Of A"])
        self.client.force_authenticate(self.b.user)
        names = [p["full_name"] for p in self.client.get(f"{BASE}/patients/").data]
        self.assertEqual(names, ["Patient Of B"])

    def test_b_requesting_a_patient_by_id_gets_404(self):
        self.client.force_authenticate(self.b.user)
        self.assertEqual(
            self.client.get(f"{BASE}/patients/{self.rel_a.pk}/").status_code, status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(
            self.client.post(f"{BASE}/patients/{self.rel_a.pk}/end/", {"reason": "other"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_access_disappears_immediately_when_patient_ends(self):
        self.client.force_authenticate(self.a.user)
        self.assertEqual(self.client.get(f"{BASE}/patients/{self.rel_a.pk}/").status_code, status.HTTP_200_OK)
        services.patient_end_relationship(patient_user=self.pa.user, confirm=True)
        self.assertEqual(self.client.get(f"{BASE}/patients/{self.rel_a.pk}/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(f"{BASE}/patients/").data, [])


class AvailabilityAPITests(APITestCase):
    def setUp(self):
        self.psych = make_psychologist()
        self.client.force_authenticate(self.psych.user)

    def test_get_and_put(self):
        self.assertEqual(self.client.get(AVAILABILITY).data, {"accepting": True, "reason": None})
        r = self.client.put(AVAILABILITY, {"accepting": False}, format="json")
        self.assertEqual(r.data, {"reason": ["Choose a reason when you're not accepting new patients."]})
        r = self.client.put(AVAILABILITY, {"accepting": False, "reason": "away"}, format="json")
        self.assertEqual(r.data, {"accepting": False, "reason": "away"})
```

Append to `core/tests/test_schema.py`, which uses pytest functions with a module-level `paths` fixture (see its existing tests):

```python
PHASE3_PATHS = {
    "/api/v1/psychologists/directory/": {"get"},
    "/api/v1/psychologists/directory/{pk}/": {"get"},
    "/api/v1/psychologists/me/availability/": {"get", "put"},
    "/api/v1/relationships/requests/": {"get", "post"},
    "/api/v1/relationships/requests/{pk}/cancel/": {"post"},
    "/api/v1/relationships/requests/{pk}/accept/": {"post"},
    "/api/v1/relationships/requests/{pk}/decline/": {"post"},
    "/api/v1/relationships/current/": {"get"},
    "/api/v1/relationships/current/end/": {"post"},
    "/api/v1/relationships/recent/": {"get"},
    "/api/v1/relationships/inbox/": {"get"},
    "/api/v1/relationships/patients/": {"get"},
    "/api/v1/relationships/patients/{pk}/": {"get"},
    "/api/v1/relationships/patients/{pk}/end/": {"post"},
    "/api/v1/relationships/history/": {"get"},
}


@pytest.mark.parametrize("path,methods", sorted(PHASE3_PATHS.items()))
def test_phase3_paths_present(paths, path, methods):
    assert path in paths
    assert methods <= set(paths[path])


def test_request_create_documents_201(paths):
    assert "201" in paths["/api/v1/relationships/requests/"]["post"]["responses"]
```

(If `pytest` isn't already imported at the top of `core/tests/test_schema.py`, add `import pytest`.)

Run: `venv/Scripts/python -m pytest apps/relationships/tests/test_api_psychologist.py core/tests/test_schema.py -q` → FAIL.

- [ ] **Step 2: Serializers**

Append to `apps/relationships/api/serializers.py` (imports: `from drf_spectacular.types import OpenApiTypes`; `from django.utils import timezone`; `from apps.reference.api.serializers import CitySerializer, CountrySerializer, LanguageSerializer`; `from apps.relationships.models import DeclineReason, PSYCHOLOGIST_END_REASONS`; `from apps.relationships.selectors import requester_summary`; `from core.validators import age_on`):

```python
ASSIGNED_PATIENT_FIELDS = [
    "relationship_id", "accepted_at", "full_name", "pseudonym", "age", "gender",
    "phone_number", "country", "city", "preferred_language", "timezone",
]


class InboxItemSerializer(serializers.ModelSerializer):
    requester = serializers.SerializerMethodField()

    class Meta:
        model = CareRelationship
        fields = ["id", "requested_at", "expires_at", "requester"]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_requester(self, obj):
        return requester_summary(relationship=obj)


class AssignedPatientSerializer(serializers.Serializer):
    """The assigned psychologist's view of a patient: real identity, age only,
    NEVER date_of_birth."""

    relationship_id = serializers.IntegerField(source="id", read_only=True)
    accepted_at = serializers.DateTimeField(source="responded_at", read_only=True)
    full_name = serializers.CharField(source="patient.user.full_name", read_only=True)
    pseudonym = serializers.CharField(source="patient.pseudonym", read_only=True)
    age = serializers.SerializerMethodField()
    gender = serializers.CharField(source="patient.gender", read_only=True, allow_null=True)
    phone_number = serializers.CharField(source="patient.phone_number", read_only=True, allow_null=True)
    country = CountrySerializer(source="patient.country", read_only=True, allow_null=True)
    city = CitySerializer(source="patient.city", read_only=True, allow_null=True)
    preferred_language = LanguageSerializer(source="patient.preferred_language", read_only=True, allow_null=True)
    timezone = serializers.CharField(source="patient.timezone", read_only=True)

    @extend_schema_field(OpenApiTypes.INT)
    def get_age(self, obj):
        dob = obj.patient.date_of_birth
        return age_on(dob, timezone.localdate()) if dob else None


class HistoryItemSerializer(serializers.Serializer):
    relationship_id = serializers.IntegerField(source="id", read_only=True)
    pseudonym = serializers.CharField(source="patient.pseudonym", read_only=True)
    accepted_at = serializers.DateTimeField(source="responded_at", read_only=True)
    ended_at = serializers.DateTimeField(read_only=True)
    ended_by = serializers.CharField(read_only=True)
    end_reason = serializers.CharField(read_only=True)


class DeclineSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    reason = serializers.ChoiceField(choices=DeclineReason.choices, required=False, allow_null=True)


class PsychologistEndSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=sorted(r.value for r in PSYCHOLOGIST_END_REASONS),
        required=False, allow_null=True,
    )
```

(`AssignedPatientSerializer`'s `ASSIGNED_PATIENT_FIELDS` must equal its declared fields; the test checks the response keys against the constant.)

Append to `apps/psychologists/api/serializers.py` (import `from apps.psychologists.models import NotAcceptingReason` alongside `PsychologistProfile`):

```python
class AvailabilitySerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    accepting = serializers.BooleanField()
    reason = serializers.ChoiceField(choices=NotAcceptingReason.choices, required=False, allow_null=True)
```

- [ ] **Step 3: Views and URLs**

Append to `apps/relationships/api/views.py` (imports: `from rest_framework.exceptions import NotFound`; `from apps.relationships.api.serializers import AssignedPatientSerializer, DeclineSerializer, HistoryItemSerializer, InboxItemSerializer, PsychologistEndSerializer`; `from core.permissions import IsPsychologist`; `from rest_framework import serializers as drf_serializers`):

```python
REQUEST_ANSWER = inline_serializer(
    "RequestAnswer", {"id": drf_serializers.IntegerField(), "status": drf_serializers.CharField()}
)
```


```python
class InboxView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @extend_schema(responses=InboxItemSerializer(many=True))
    def get(self, request):
        rows = selectors.psychologist_inbox(psychologist_user=request.user)
        return Response(InboxItemSerializer(rows, many=True).data)


class AcceptRequestView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @extend_schema(request=None, responses=REQUEST_ANSWER)
    def post(self, request, pk):
        rel = _domain(services.accept_request, psychologist_user=request.user, relationship_id=pk)
        return Response({"id": rel.pk, "status": rel.status})


class DeclineRequestView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @extend_schema(request=DeclineSerializer, responses=REQUEST_ANSWER)
    def post(self, request, pk):
        body = DeclineSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        rel = _domain(
            services.decline_request, psychologist_user=request.user,
            relationship_id=pk, reason=body.validated_data.get("reason"),
        )
        return Response({"id": rel.pk, "status": rel.status})


class PatientListView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @extend_schema(responses=AssignedPatientSerializer(many=True))
    def get(self, request):
        rows = selectors.psychologist_patients(psychologist_user=request.user)
        return Response(AssignedPatientSerializer(rows, many=True).data)


class PatientDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @extend_schema(responses=AssignedPatientSerializer)
    def get(self, request, pk):
        rel = selectors.psychologist_patient(psychologist_user=request.user, relationship_id=pk)
        if rel is None:
            raise NotFound()
        return Response(AssignedPatientSerializer(rel).data)


class PatientEndView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @extend_schema(request=PsychologistEndSerializer, responses=HistoryItemSerializer)
    def post(self, request, pk):
        body = PsychologistEndSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        rel = _domain(
            services.psychologist_end_relationship, psychologist_user=request.user,
            relationship_id=pk, reason=body.validated_data.get("reason"),
        )
        return Response(HistoryItemSerializer(rel).data)


class HistoryView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @extend_schema(responses=HistoryItemSerializer(many=True))
    def get(self, request):
        rows = selectors.psychologist_history(psychologist_user=request.user)
        return Response(HistoryItemSerializer(rows, many=True).data)
```

Add to `apps/relationships/api/urls.py` (import the new views):

```python
    path("requests/<int:pk>/accept/", AcceptRequestView.as_view(), name="request-accept"),
    path("requests/<int:pk>/decline/", DeclineRequestView.as_view(), name="request-decline"),
    path("inbox/", InboxView.as_view(), name="inbox"),
    path("patients/", PatientListView.as_view(), name="patients"),
    path("patients/<int:pk>/", PatientDetailView.as_view(), name="patient-detail"),
    path("patients/<int:pk>/end/", PatientEndView.as_view(), name="patient-end"),
    path("history/", HistoryView.as_view(), name="history"),
```

Append to `apps/psychologists/api/views.py` (imports: `from apps.psychologists.api.serializers import AvailabilitySerializer`; `from apps.relationships import services as relationship_services`):

```python
class AvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsPsychologist]

    @staticmethod
    def _payload(profile):
        return {"accepting": profile.is_accepting_patients, "reason": profile.not_accepting_reason}

    @extend_schema(responses=AvailabilitySerializer)
    def get(self, request):
        profile = selectors.get_psychologist_profile_for_user(user=request.user)
        if profile is None:
            raise NotFound("Profile not found.")
        return Response(self._payload(profile))

    @extend_schema(request=AvailabilitySerializer, responses=AvailabilitySerializer)
    def put(self, request):
        body = AvailabilitySerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            profile = relationship_services.set_accepting_status(
                psychologist_user=request.user,
                accepting=body.validated_data["accepting"],
                reason=body.validated_data.get("reason"),
            )
        except DomainValidationError as exc:
            raise ValidationError(exc.errors, code=exc.code) from exc
        return Response(self._payload(profile))
```

Add to `apps/psychologists/api/urls.py`: `path("me/availability/", AvailabilityView.as_view(), name="availability"),`.

Run: `venv/Scripts/python -m pytest apps/relationships core/tests/test_schema.py apps/psychologists -q` → PASS; full suite → all pass; `venv/Scripts/python manage.py spectacular --file <scratch>/schema.yml --settings config.settings.test` → no `Error`/`Warning` lines for the new views (report the output).

- [ ] **Step 4: Module-reference + commit**

Rows for `InboxView`, `AcceptRequestView`, `DeclineRequestView`, `PatientListView`, `PatientDetailView`, `PatientEndView`, `HistoryView` (MindCare Web; history = psychologist's pseudonym-only list) and `AvailabilityView` (`GET`/`PUT /api/v1/psychologists/me/availability/`, MindCare Web).

```bash
git add apps/relationships/api/serializers.py apps/relationships/api/views.py apps/relationships/api/urls.py apps/relationships/tests/test_api_psychologist.py apps/psychologists/api/serializers.py apps/psychologists/api/views.py apps/psychologists/api/urls.py core/tests/test_schema.py docs/module-reference.md
git commit -m "feat(relationships): psychologist API - inbox, answer, patients, history, end, availability

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Docs, full verification, local migration and schema check

**Files:**
- Modify: `docs/architecture.md`, `docs/module-reference.md` (consistency pass only)

- [ ] **Step 1: Docs (implementer)**

`docs/architecture.md`, Modules list: add after `psychologists`:

```markdown
- **relationships** — psychologist ↔ patient care relationships: requests, acceptance,
  ending, and the ownership rules every psychologist-facing query uses.
```

and change the `psychologists` bullet to: "psychologist profiles, credentials, the patient-facing directory and the accepting-new-patients switch." Confirm `module-reference.md` has a row for every new service, selector, view, serializer-facing endpoint and the auth class, with no duplicate sections.

Run: `venv/Scripts/python -m pytest -q` → all pass, no warnings. `venv/Scripts/python manage.py makemigrations --check --dry-run --settings config.settings.test` → "No changes detected". From the repo root: `pre-commit run --all-files` → clean.

```bash
git add docs/architecture.md docs/module-reference.md
git commit -m "docs: relationships module in architecture; module-reference consistency

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 2: Local migration and schema check (CONTROLLER ONLY, not the implementer)**

Run through the guarded helper used in Phase 2 (explicit `DATABASE_URL=postgresql://mindcare:mindcare@localhost:5432/mindcare`, aborts unless the host is local): `migrate`. Expected: `accounts.0003`, `psychologists.0002`, `relationships.0001` applied. Then inside the Docker container:

```sql
SELECT table_name FROM information_schema.tables WHERE table_name = 'relationships_carerelationship';
SELECT indexname, indexdef FROM pg_indexes
 WHERE indexname IN ('relationships_one_open_per_patient', 'relationships_psych_status_idx');
-- expect the partial unique index WHERE status IN ('pending','accepted')
SELECT column_name, is_nullable FROM information_schema.columns
 WHERE (table_name = 'accounts_user' AND column_name = 'last_active_at')
    OR (table_name = 'psychologists_psychologistprofile'
        AND column_name IN ('is_accepting_patients', 'not_accepting_reason'));
SELECT conname, confdeltype FROM pg_constraint
 WHERE conrelid = 'relationships_carerelationship'::regclass AND contype = 'f';
-- expect two FKs with confdeltype 'a' (NO ACTION): Django enforces PROTECT in Python
```

Production gets these migrations through Render's build command after merge.
