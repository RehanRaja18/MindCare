"""Model-level tests for CareRelationship (constraint and codes)."""

from unittest import mock

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
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
        patient=patient,
        psychologist=psychologist,
        status=status,
        requested_at=now,
        expires_at=now + REQUEST_EXPIRY,
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
        self.assertEqual(
            CareRelationship.objects.filter(patient=self.patient).count(), 5
        )

    def test_accepted_row_also_blocks_a_second_open_row(self):
        _row(self.patient, self.a, RelationshipStatus.ACCEPTED)
        for status in (RelationshipStatus.PENDING, RelationshipStatus.ACCEPTED):
            with self.subTest(status=status):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    _row(self.patient, self.b, status)


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


class ProtectTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()
        _row(self.patient, self.psych, RelationshipStatus.ENDED)

    def test_patient_profile_with_relationship_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.patient.delete()
        self.assertTrue(type(self.patient).objects.filter(pk=self.patient.pk).exists())

    def test_psychologist_profile_with_relationship_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.psych.delete()
        self.assertTrue(type(self.psych).objects.filter(pk=self.psych.pk).exists())


class EffectiveStatusTests(TestCase):
    """Read-only expiry on read; no DB access needed (unsaved instances)."""

    def _rel(self, status, expires_at):
        return CareRelationship(status=status, expires_at=expires_at)

    def test_live_pending_stays_pending(self):
        rel = self._rel(RelationshipStatus.PENDING, timezone.now() + REQUEST_EXPIRY)
        self.assertEqual(rel.effective_status, RelationshipStatus.PENDING)

    def test_pending_at_exactly_expires_at_is_expired(self):
        fixed = timezone.now()
        rel = self._rel(RelationshipStatus.PENDING, fixed)
        with mock.patch("apps.relationships.models.timezone.now", return_value=fixed):
            self.assertEqual(rel.effective_status, RelationshipStatus.EXPIRED)
        self.assertEqual(rel.status, RelationshipStatus.PENDING)

    def test_non_pending_statuses_unchanged_even_when_past_expiry(self):
        past = timezone.now() - REQUEST_EXPIRY
        for status in RelationshipStatus.values:
            if status == RelationshipStatus.PENDING:
                continue
            with self.subTest(status=status):
                self.assertEqual(self._rel(status, past).effective_status, status)
