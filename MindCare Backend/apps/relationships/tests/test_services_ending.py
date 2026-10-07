"""Service tests: ending, unavailable accounts, pause, availability."""

import json
from unittest.mock import patch

from django.db import transaction
from django.http import Http404
from django.test import TestCase

from apps.accounts.models import ApprovalStatus
from apps.relationships import selectors, services
from apps.relationships.models import RelationshipStatus
from core.exceptions import DomainValidationError
from core.testing import make_patient, make_psychologist


def _accepted(patient, psych):
    rel = services.request_psychologist(
        patient_user=patient.user, psychologist_id=psych.pk
    )
    return services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)


class EndRelationshipTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.psych = make_psychologist()
        self.rel = _accepted(self.patient, self.psych)

    def test_patient_ends_with_confirm(self):
        rel = services.patient_end_relationship(
            patient_user=self.patient.user, confirm=True
        )
        self.assertEqual(
            (rel.status, rel.ended_by, rel.end_reason),
            (RelationshipStatus.ENDED, "patient", "patient_ended"),
        )
        self.assertIsNotNone(rel.ended_at)

    def test_patient_must_confirm_with_true(self):
        for value in (False, None, "true", 1):
            with self.subTest(value=value), self.assertRaises(
                DomainValidationError
            ) as ctx:
                services.patient_end_relationship(
                    patient_user=self.patient.user, confirm=value
                )
            self.assertEqual(
                ctx.exception.errors,
                {"confirm": ["Confirm that you want to end this relationship."]},
            )

    def test_patient_without_psychologist(self):
        with self.assertRaises(DomainValidationError) as ctx:
            services.patient_end_relationship(
                patient_user=make_patient().user, confirm=True
            )
        self.assertEqual(
            ctx.exception.errors,
            {"relationship": ["You don't have a psychologist right now."]},
        )

    def test_psychologist_end_requires_reason_from_their_list(self):
        with self.assertRaises(DomainValidationError) as ctx:
            services.psychologist_end_relationship(
                psychologist_user=self.psych.user,
                relationship_id=self.rel.pk,
                reason=None,
            )
        self.assertEqual(ctx.exception.errors, {"reason": ["Choose a reason."]})
        for bad in ("patient_unresponsive", "patient_ended", "subscription_lapsed"):
            with self.subTest(reason=bad), self.assertRaises(DomainValidationError):
                services.psychologist_end_relationship(
                    psychologist_user=self.psych.user,
                    relationship_id=self.rel.pk,
                    reason=bad,
                )
        rel = services.psychologist_end_relationship(
            psychologist_user=self.psych.user,
            relationship_id=self.rel.pk,
            reason="treatment_completed",
        )
        self.assertEqual(
            (rel.ended_by, rel.end_reason), ("psychologist", "treatment_completed")
        )

    def test_other_psychologist_gets_404(self):
        with self.assertRaises(Http404):
            services.psychologist_end_relationship(
                psychologist_user=make_psychologist().user,
                relationship_id=self.rel.pk,
                reason="other",
            )
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)

    def test_psychologist_end_after_patient_ended_between_read_and_lock_is_404(self):
        # The patient ends the row after psychologist_end_relationship's unlocked
        # read finds it, but before end_relationship locks it. The psychologist
        # must get the same 404 as when the read itself misses.
        real_end = services.end_relationship

        def patient_wins_first(**kwargs):
            real_end(
                relationship=self.rel,
                ended_by="patient",
                reason="patient_ended",
                actor_id=self.patient.user.pk,
            )
            return real_end(**kwargs)

        with patch.object(services, "end_relationship", side_effect=patient_wins_first):
            with self.assertRaises(Http404):
                services.psychologist_end_relationship(
                    psychologist_user=self.psych.user,
                    relationship_id=self.rel.pk,
                    reason="other",
                )
        self.rel.refresh_from_db()
        self.assertEqual(
            (self.rel.status, self.rel.ended_by), (RelationshipStatus.ENDED, "patient")
        )

    def test_unapproved_or_inactive_psychologist_cannot_end(self):
        user = self.psych.user
        for changes in (
            {"approval_status": ApprovalStatus.PENDING},
            {"is_active": False},
        ):
            with self.subTest(changes=changes):
                for field, value in changes.items():
                    setattr(user, field, value)
                user.save()
                with self.assertRaises(Http404):
                    services.psychologist_end_relationship(
                        psychologist_user=user,
                        relationship_id=self.rel.pk,
                        reason="other",
                    )
                self.rel.refresh_from_db()
                self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
                user.approval_status = ApprovalStatus.APPROVED
                user.is_active = True
                user.save()

    def test_subscription_lapsed_is_system_only(self):
        with self.assertRaises(DomainValidationError):
            services.end_relationship(
                relationship=self.rel, ended_by="patient", reason="subscription_lapsed"
            )
        rel = services.end_relationship(
            relationship=self.rel, ended_by="system", reason="subscription_lapsed"
        )
        self.assertEqual(rel.end_reason, "subscription_lapsed")

    def test_ending_twice_is_rejected(self):
        services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        with self.assertRaises(DomainValidationError):
            services.end_relationship(
                relationship=self.rel, ended_by="system", reason="account_unavailable"
            )

    def test_no_cooldown_after_psychologist_ends(self):
        services.psychologist_end_relationship(
            psychologist_user=self.psych.user,
            relationship_id=self.rel.pk,
            reason="other",
        )
        again = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )
        self.assertEqual(again.status, RelationshipStatus.PENDING)

    def test_ended_event_logged_with_ids_and_codes_only(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            with self.captureOnCommitCallbacks(execute=True):
                services.psychologist_end_relationship(
                    psychologist_user=self.psych.user,
                    relationship_id=self.rel.pk,
                    reason="referred_elsewhere",
                )
        payload = json.loads(captured.records[-1].getMessage())
        self.assertEqual(
            (
                payload["event"],
                payload["actor_role"],
                payload["reason"],
                payload["actor_id"],
            ),
            ("ended", "psychologist", "referred_elsewhere", self.psych.user.pk),
        )
        self.assertNotIn("patient_id", payload)


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

    def test_logs_ended_and_expired_after_commit(self):
        psych_with_both = make_psychologist()
        patient_a, patient_b = make_patient(), make_patient()
        accepted = _accepted(patient_a, psych_with_both)
        pending = services.request_psychologist(
            patient_user=patient_b.user, psychologist_id=psych_with_both.pk
        )
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            with self.captureOnCommitCallbacks(execute=True):
                services.end_for_unavailable_account(user=psych_with_both.user)
        events = {
            (p["relationship_id"], p["event"], p["actor_role"])
            for p in (json.loads(r.getMessage()) for r in captured.records)
        }
        self.assertEqual(
            events,
            {(accepted.pk, "ended", "system"), (pending.pk, "expired", "system")},
        )

    def test_rolled_back_outer_transaction_logs_nothing_and_changes_nothing(self):
        class Boom(Exception):
            pass

        with self.assertNoLogs("mindcare.audit", level="INFO"):
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        services.end_for_unavailable_account(user=self.psych.user)
                        services.end_for_unavailable_account(
                            user=self.other_patient.user
                        )
                        raise Boom
                except Boom:
                    pass
        self.rel.refresh_from_db()
        self.pending.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
        self.assertIsNone(self.rel.ended_at)
        self.assertEqual(self.pending.status, RelationshipStatus.PENDING)

    def test_becoming_pending_is_a_pause_not_an_end(self):
        user = self.psych.user
        user.approval_status = ApprovalStatus.PENDING
        user.save()  # no end_for_unavailable_account call for pending
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
        self.assertFalse(
            selectors.is_assigned_psychologist(
                viewer=user, patient_profile=self.patient
            )
        )
        self.assertIsNone(selectors.get_active_relationship(patient=self.patient))
        rel = services.patient_end_relationship(
            patient_user=self.patient.user, confirm=True
        )
        self.assertEqual(rel.status, RelationshipStatus.ENDED)


class AvailabilityTests(TestCase):
    def setUp(self):
        self.psych = make_psychologist()

    def test_reason_required_when_off_and_cleared_when_on(self):
        with self.assertRaises(DomainValidationError) as ctx:
            services.set_accepting_status(
                psychologist_user=self.psych.user, accepting=False
            )
        self.assertEqual(
            ctx.exception.errors,
            {"reason": ["Choose a reason when you're not accepting new patients."]},
        )
        profile = services.set_accepting_status(
            psychologist_user=self.psych.user, accepting=False, reason="fully_booked"
        )
        self.assertEqual(
            (profile.is_accepting_patients, profile.not_accepting_reason),
            (False, "fully_booked"),
        )
        profile = services.set_accepting_status(
            psychologist_user=self.psych.user, accepting=True, reason="away"
        )
        self.assertEqual(
            (profile.is_accepting_patients, profile.not_accepting_reason), (True, None)
        )

    def test_unknown_reason_rejected(self):
        with self.assertRaises(DomainValidationError):
            services.set_accepting_status(
                psychologist_user=self.psych.user, accepting=False, reason="sick"
            )

    def test_switching_off_leaves_pending_requests_answerable(self):
        patient = make_patient()
        rel = services.request_psychologist(
            patient_user=patient.user, psychologist_id=self.psych.pk
        )
        expires_at = rel.expires_at
        services.set_accepting_status(
            psychologist_user=self.psych.user, accepting=False, reason="fully_booked"
        )
        rel.refresh_from_db()
        self.assertEqual(rel.status, RelationshipStatus.PENDING)
        self.assertEqual(rel.expires_at, expires_at)
        self.assertIsNone(rel.responded_at)
        self.assertIsNone(rel.cooldown_until)
        accepted = services.accept_request(
            psychologist_user=self.psych.user, relationship_id=rel.pk
        )
        self.assertEqual(accepted.status, RelationshipStatus.ACCEPTED)
