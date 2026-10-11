"""Tests for the demo seed (apps/accounts/demo.py) and the seed_demo command."""

import os
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts import demo
from apps.accounts.models import ApprovalStatus, Role, User
from apps.patients.models import PatientProfile
from apps.psychologists.models import PsychologistProfile
from apps.relationships import selectors as relationship_selectors
from apps.relationships import services as relationship_services
from apps.relationships.models import CareRelationship, RelationshipStatus
from core.testing import make_patient, make_psychologist

PASSWORD = "demo-pass-123"


class SeedDemoServiceTests(TestCase):
    def test_creates_six_approved_psychologists_and_two_patients(self):
        demo.seed_demo_accounts(password=PASSWORD)

        psychs = PsychologistProfile.objects.filter(
            user__email__in=demo.DEMO_PSYCHOLOGIST_EMAILS
        )
        self.assertEqual(psychs.count(), 6)
        for p in psychs:
            self.assertEqual(p.user.approval_status, ApprovalStatus.APPROVED)
            self.assertTrue(p.user.is_active)
            self.assertTrue(p.user.email.endswith("@example.com"))
            self.assertNotIn("(Demo)", p.user.full_name)
            self.assertTrue(p.bio.startswith("Demo account, not a real psychologist."))
            self.assertTrue(p.user.check_password(PASSWORD))
            self.assertTrue(p.specializations.exists())
            self.assertTrue(p.languages.exists())

        accepting = {p.is_accepting_patients for p in psychs}
        self.assertEqual(accepting, {True, False})
        for p in psychs.filter(is_accepting_patients=False):
            self.assertTrue(p.not_accepting_reason)
        self.assertGreater(len({p.city_id for p in psychs}), 3)
        self.assertGreater(len({p.gender for p in psychs}), 1)
        specs = set(psychs.values_list("specializations__slug", flat=True))
        self.assertGreater(len(specs), 4)

        patients = PatientProfile.objects.filter(
            user__email__in=demo.DEMO_PATIENT_EMAILS
        )
        self.assertEqual(patients.count(), 2)
        for p in patients:
            self.assertEqual(p.user.role, Role.PATIENT)
            self.assertIsNotNone(p.date_of_birth)
            self.assertTrue(p.timezone)
            self.assertTrue(p.user.check_password(PASSWORD))

    def test_rerun_renames_accounts_seeded_with_the_old_demo_suffix(self):
        demo.seed_demo_accounts(password=PASSWORD)
        # Simulate production rows written before the name rule existed.
        User.objects.filter(email__in=demo.DEMO_EMAILS).update(
            full_name="Dr. Old Name (Demo)"
        )
        sara = PsychologistProfile.objects.get(user__email=demo.DEMO_INBOX_PSYCHOLOGIST)
        PsychologistProfile.objects.filter(pk=sara.pk).update(bio="Demo profile.")

        demo.seed_demo_accounts(password=PASSWORD)

        names = set(
            User.objects.filter(email__in=demo.DEMO_EMAILS).values_list(
                "full_name", flat=True
            )
        )
        self.assertEqual(
            names,
            {
                spec["full_name"]
                for spec in demo.DEMO_PSYCHOLOGISTS + demo.DEMO_PATIENTS
            },
        )
        sara.refresh_from_db()
        self.assertTrue(sara.bio.startswith("Demo account, not a real psychologist."))

    def test_is_idempotent(self):
        first = demo.seed_demo_accounts(password=PASSWORD)
        second = demo.seed_demo_accounts(password=PASSWORD)
        self.assertEqual(first["created"], 8)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["existing"], 8)
        self.assertEqual(User.objects.filter(email__in=demo.DEMO_EMAILS).count(), 8)

    def test_seeds_accepted_and_pending_relationships_with_one_psychologist(self):
        demo.seed_demo_accounts(password=PASSWORD)
        sara = PsychologistProfile.objects.get(user__email=demo.DEMO_INBOX_PSYCHOLOGIST)
        p1, p2 = (
            PatientProfile.objects.get(user__email=e) for e in demo.DEMO_PATIENT_EMAILS
        )
        accepted = relationship_selectors.patient_current(patient_user=p1.user)
        pending = relationship_selectors.patient_current(patient_user=p2.user)
        self.assertEqual(
            (accepted.psychologist, accepted.status),
            (sara, RelationshipStatus.ACCEPTED),
        )
        self.assertEqual(
            (pending.psychologist, pending.status), (sara, RelationshipStatus.PENDING)
        )
        self.assertEqual(
            list(
                relationship_selectors.psychologist_inbox(psychologist_user=sara.user)
            ),
            [pending],
        )
        self.assertEqual(
            [
                r.pk
                for r in relationship_selectors.psychologist_patients(
                    psychologist_user=sara.user
                )
            ],
            [accepted.pk],
        )

    def test_rerun_keeps_relationships_and_renews_an_expired_request(self):
        demo.seed_demo_accounts(password=PASSWORD)
        demo.seed_demo_accounts(password=PASSWORD)
        self.assertEqual(CareRelationship.objects.count(), 2)

        p2 = PatientProfile.objects.get(user__email=demo.DEMO_PATIENT_EMAILS[1])
        CareRelationship.objects.filter(patient=p2).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        demo.seed_demo_accounts(password=PASSWORD)
        current = relationship_selectors.patient_current(patient_user=p2.user)
        self.assertEqual(current.status, RelationshipStatus.PENDING)
        self.assertEqual(CareRelationship.objects.filter(patient=p2).count(), 2)

    def test_remove_deletes_only_demo_accounts_relationships_first(self):
        demo.seed_demo_accounts(password=PASSWORD)  # 2 demo relationship rows
        real_patient = make_patient()
        real_psych = make_psychologist()
        other_demo_psych = PsychologistProfile.objects.get(
            user__email="demo.psych.bilal@example.com"
        )
        # PROTECT rows: a real patient -> demo psych (removed), and a real
        # patient -> real psych (kept).
        relationship_services.request_psychologist(
            patient_user=real_patient.user, psychologist_id=other_demo_psych.pk
        )
        other_real = make_patient()
        kept = relationship_services.request_psychologist(
            patient_user=other_real.user, psychologist_id=real_psych.pk
        )

        result = demo.remove_demo_accounts()

        self.assertEqual(result["users"], 8)
        self.assertEqual(result["relationships"], 3)
        self.assertFalse(User.objects.filter(email__in=demo.DEMO_EMAILS).exists())
        self.assertTrue(User.objects.filter(pk=real_patient.user.pk).exists())
        self.assertTrue(User.objects.filter(pk=real_psych.user.pk).exists())
        self.assertEqual(list(CareRelationship.objects.all()), [kept])

    def test_remove_with_nothing_seeded_is_a_no_op(self):
        self.assertEqual(demo.remove_demo_accounts(), {"users": 0, "relationships": 0})


class SeedDemoCommandTests(TestCase):
    def test_requires_demo_password_env_var(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEMO_PASSWORD", None)
            with self.assertRaisesMessage(CommandError, "DEMO_PASSWORD"):
                call_command("seed_demo", stdout=StringIO())
        self.assertFalse(User.objects.filter(email__in=demo.DEMO_EMAILS).exists())

    def test_seeds_with_env_password_and_never_prints_it(self):
        out = StringIO()
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": PASSWORD}):
            call_command("seed_demo", stdout=out)
        self.assertEqual(User.objects.filter(email__in=demo.DEMO_EMAILS).count(), 8)
        self.assertNotIn(PASSWORD, out.getvalue())

    def test_remove_option_needs_no_password(self):
        demo.seed_demo_accounts(password=PASSWORD)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEMO_PASSWORD", None)
            call_command("seed_demo", "--remove", stdout=StringIO())
        self.assertFalse(User.objects.filter(email__in=demo.DEMO_EMAILS).exists())
