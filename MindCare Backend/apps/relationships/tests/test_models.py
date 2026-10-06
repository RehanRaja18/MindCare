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
