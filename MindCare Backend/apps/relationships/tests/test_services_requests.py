"""Service tests: requesting, cancelling, accepting, declining, expiry."""

from datetime import timedelta
from unittest.mock import patch

from django.http import Http404
from django.test import TestCase

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
            {
                "date_of_birth": [
                    "Add your date of birth to your profile before requesting a psychologist."
                ]
            },
        )

    def test_same_generic_error_for_unavailable_psychologists(self):
        pending = make_psychologist(approval_status=ApprovalStatus.PENDING)
        rejected = make_psychologist(approval_status=ApprovalStatus.REJECTED)
        inactive = make_psychologist(is_active=False)
        for psych_id in (pending.pk, rejected.pk, inactive.pk, 999999):
            with self.subTest(psych_id=psych_id), self.assertRaises(
                DomainValidationError
            ) as ctx:
                self._request(psych_id=psych_id)
            self.assertEqual(
                ctx.exception.errors,
                {"psychologist": ["This psychologist isn't available."]},
            )

    def test_not_accepting(self):
        self.psych.is_accepting_patients = False
        self.psych.not_accepting_reason = "fully_booked"
        self.psych.save()
        with self.assertRaises(DomainValidationError) as ctx:
            self._request()
        self.assertEqual(
            ctx.exception.errors,
            {
                "psychologist": [
                    "This psychologist isn't accepting new patients right now."
                ]
            },
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
        services.decline_request(
            psychologist_user=self.psych.user, relationship_id=rel.pk
        )
        rel.refresh_from_db()
        day29 = rel.responded_at + timedelta(days=29)
        with patch("django.utils.timezone.now", return_value=day29):
            with self.assertRaises(DomainValidationError) as ctx:
                self._request()
        message = ctx.exception.errors["psychologist"][0]
        self.assertTrue(
            message.startswith("You can request this psychologist again on ")
        )
        with patch(
            "django.utils.timezone.now",
            return_value=rel.responded_at + DECLINE_COOLDOWN,
        ):
            self.assertEqual(self._request().status, RelationshipStatus.PENDING)

    def test_no_cooldown_after_cancel(self):
        rel = self._request()
        services.cancel_request(patient_user=self.patient.user, relationship_id=rel.pk)
        self.assertEqual(self._request().status, RelationshipStatus.PENDING)

    def test_simultaneous_request_integrity_error_becomes_400(self):
        from django.db import IntegrityError

        with patch.object(
            CareRelationship.objects, "create", side_effect=IntegrityError("dup")
        ):
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
        rel = services.accept_request(
            psychologist_user=self.psych.user, relationship_id=self.rel.pk
        )
        self.assertEqual(rel.status, RelationshipStatus.ACCEPTED)
        self.assertIsNotNone(rel.responded_at)

    def test_accept_allowed_while_not_accepting(self):
        self.psych.is_accepting_patients = False
        self.psych.not_accepting_reason = "away"
        self.psych.save()
        rel = services.accept_request(
            psychologist_user=self.psych.user, relationship_id=self.rel.pk
        )
        self.assertEqual(rel.status, RelationshipStatus.ACCEPTED)

    def test_other_psychologist_gets_404(self):
        with self.assertRaises(Http404):
            services.accept_request(
                psychologist_user=make_psychologist().user, relationship_id=self.rel.pk
            )

    def test_other_patient_cannot_cancel(self):
        with self.assertRaises(Http404):
            services.cancel_request(
                patient_user=make_patient().user, relationship_id=self.rel.pk
            )

    def test_deactivated_psychologist_cannot_accept(self):
        self.psych.user.is_active = False
        self.psych.user.save()
        with self.assertRaises(Http404):
            services.accept_request(
                psychologist_user=self.psych.user, relationship_id=self.rel.pk
            )

    def test_expired_request_cannot_be_accepted_and_is_marked_expired(self):
        later = self.rel.expires_at + timedelta(seconds=1)
        with patch("django.utils.timezone.now", return_value=later):
            with self.assertRaises(DomainValidationError) as ctx:
                services.accept_request(
                    psychologist_user=self.psych.user, relationship_id=self.rel.pk
                )
        self.assertEqual(
            ctx.exception.errors,
            {"relationship": ["This request is no longer pending."]},
        )
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.EXPIRED)

    def test_decline_with_reason_sets_cooldown(self):
        rel = services.decline_request(
            psychologist_user=self.psych.user,
            relationship_id=self.rel.pk,
            reason="outside_specializations",
        )
        self.assertEqual(rel.status, RelationshipStatus.DECLINED)
        self.assertEqual(rel.decline_reason, "outside_specializations")
        self.assertEqual(rel.cooldown_until - rel.responded_at, DECLINE_COOLDOWN)

    def test_decline_rejects_unknown_reason(self):
        with self.assertRaises(DomainValidationError):
            services.decline_request(
                psychologist_user=self.psych.user,
                relationship_id=self.rel.pk,
                reason="rude",
            )

    def test_cancel_then_accept_is_not_pending(self):
        services.cancel_request(
            patient_user=self.patient.user, relationship_id=self.rel.pk
        )
        with self.assertRaises(DomainValidationError):
            services.accept_request(
                psychologist_user=self.psych.user, relationship_id=self.rel.pk
            )

    def test_events_logged_with_ids_only(self):
        import json

        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            services.accept_request(
                psychologist_user=self.psych.user, relationship_id=self.rel.pk
            )
        payload = json.loads(captured.records[-1].getMessage())
        self.assertEqual(payload["event"], "accepted")
        self.assertEqual(payload["actor_role"], "psychologist")
        self.assertNotIn("patient_id", payload)
