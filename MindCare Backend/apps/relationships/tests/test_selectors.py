"""Selector tests for relationships."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ApprovalStatus
from apps.relationships import selectors
from apps.relationships.models import (
    REQUEST_EXPIRY,
    CareRelationship,
    RelationshipStatus,
)
from core.testing import make_patient, make_psychologist


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
        self.assertFalse(
            selectors.is_assigned_psychologist(
                viewer=viewer, patient_profile=self.patient
            )
        )
        rel.status = RelationshipStatus.ACCEPTED
        rel.save()
        self.assertTrue(
            selectors.is_assigned_psychologist(
                viewer=viewer, patient_profile=self.patient
            )
        )
        viewer.approval_status = ApprovalStatus.PENDING  # paused (re-review)
        viewer.save()
        self.assertFalse(
            selectors.is_assigned_psychologist(
                viewer=viewer, patient_profile=self.patient
            )
        )

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
        _row(
            other_patient,
            self.psych,
            RelationshipStatus.PENDING,
            requested_at=past,
            expires_at=past + REQUEST_EXPIRY,
        )
        self.assertEqual(
            list(selectors.psychologist_inbox(psychologist_user=self.psych.user)),
            [live],
        )

    def test_psychologist_patients_only_while_visible(self):
        rel = _row(self.patient, self.psych, RelationshipStatus.ACCEPTED)
        self.assertEqual(
            list(selectors.psychologist_patients(psychologist_user=self.psych.user)),
            [rel],
        )
        self.psych.user.approval_status = ApprovalStatus.PENDING
        self.psych.user.save()
        self.assertEqual(
            list(selectors.psychologist_patients(psychologist_user=self.psych.user)), []
        )

    def test_patient_current_ignores_expired_pending(self):
        past = timezone.now() - timedelta(days=4)
        _row(
            self.patient,
            self.psych,
            RelationshipStatus.PENDING,
            requested_at=past,
            expires_at=past + REQUEST_EXPIRY,
        )
        self.assertIsNone(selectors.patient_current(patient_user=self.patient.user))

    def test_recent_psychologists_rules(self):
        psychs = [make_psychologist() for _ in range(12)]
        base = timezone.now() - timedelta(days=100)
        for i, p in enumerate(psychs):
            _row(
                self.patient,
                p,
                RelationshipStatus.ENDED,
                ended_at=base + timedelta(days=i),
            )
        _row(
            self.patient,
            psychs[0],
            RelationshipStatus.ENDED,
            ended_at=base + timedelta(days=50),
        )  # duplicate psych
        psychs[11].user.is_active = False  # not visible
        psychs[11].user.save()
        _row(
            self.patient, psychs[10], RelationshipStatus.PENDING
        )  # current/pending excluded
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
