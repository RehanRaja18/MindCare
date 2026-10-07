"""Tests for the demo seed (apps/accounts/demo.py) and the seed_demo command."""

import os
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.accounts import demo
from apps.accounts.models import ApprovalStatus, Role, User
from apps.patients.models import PatientProfile
from apps.psychologists.models import PsychologistProfile
from apps.relationships import services as relationship_services
from apps.relationships.models import CareRelationship
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
            self.assertIn("(Demo)", p.user.full_name)
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

    def test_is_idempotent(self):
        first = demo.seed_demo_accounts(password=PASSWORD)
        second = demo.seed_demo_accounts(password=PASSWORD)
        self.assertEqual(first["created"], 8)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["existing"], 8)
        self.assertEqual(User.objects.filter(email__in=demo.DEMO_EMAILS).count(), 8)

    def test_remove_deletes_only_demo_accounts_relationships_first(self):
        demo.seed_demo_accounts(password=PASSWORD)
        real_patient = make_patient()
        real_psych = make_psychologist()
        demo_patient = PatientProfile.objects.get(
            user__email=demo.DEMO_PATIENT_EMAILS[0]
        )
        demo_psych = PsychologistProfile.objects.filter(
            user__email__in=demo.DEMO_PSYCHOLOGIST_EMAILS, is_accepting_patients=True
        ).first()
        # PROTECT rows in both directions: demo patient -> demo psych, and a real
        # patient -> demo psych (removed), real patient 2 -> real psych (kept).
        relationship_services.request_psychologist(
            patient_user=demo_patient.user, psychologist_id=demo_psych.pk
        )
        relationship_services.request_psychologist(
            patient_user=real_patient.user, psychologist_id=demo_psych.pk
        )
        other_real = make_patient()
        kept = relationship_services.request_psychologist(
            patient_user=other_real.user, psychologist_id=real_psych.pk
        )

        result = demo.remove_demo_accounts()

        self.assertEqual(result["users"], 8)
        self.assertEqual(result["relationships"], 2)
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
