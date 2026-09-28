"""Selector tests for patients, focused on the display-identity privacy rules."""

import json

from django.test import TestCase

from apps.accounts.models import Role
from apps.patients.selectors import get_patient_display_identity
from apps.patients.services import create_patient_profile, update_patient_profile
from core.testing import make_admin, make_user


class DisplayIdentityTests(TestCase):
    def setUp(self):
        self.patient = make_user(role=Role.PATIENT, full_name="Ayesha Khan")
        self.profile = create_patient_profile(user=self.patient, timezone="UTC")

    def _identity(self, viewer):
        return get_patient_display_identity(patient_profile=self.profile, viewer=viewer)

    def test_result_has_only_two_keys(self):
        self.assertEqual(set(self._identity(None)), {"display_name", "is_real_name"})

    def test_patient_sees_own_real_name(self):
        self.assertEqual(self._identity(self.patient)["display_name"], "Ayesha Khan")

    def test_anonymous_and_other_patients_see_pseudonym_when_private(self):
        for viewer in [None, make_user(role=Role.PATIENT)]:
            result = self._identity(viewer)
            self.assertEqual(result["display_name"], self.profile.pseudonym)
            self.assertFalse(result["is_real_name"])

    def test_psychologist_sees_pseudonym_until_phase3(self):
        self.assertFalse(
            self._identity(make_user(role=Role.PSYCHOLOGIST))["is_real_name"]
        )

    def test_public_profile_shows_real_name_to_anyone(self):
        update_patient_profile(profile=self.profile, is_profile_public=True)
        self.assertEqual(self._identity(None)["display_name"], "Ayesha Khan")

    def test_admin_on_private_profile_sees_real_name_and_is_logged_with_ids_only(self):
        admin = make_admin()
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            result = self._identity(admin)
        self.assertTrue(result["is_real_name"])
        self.assertEqual(len(captured.records), 1)
        message = captured.records[0].getMessage()
        payload = json.loads(message)
        self.assertEqual(payload["event_type"], "identity_reveal")
        self.assertEqual(payload["viewer_id"], admin.pk)
        self.assertEqual(payload["patient_id"], self.patient.pk)
        self.assertNotIn("Ayesha", message)
        self.assertNotIn(self.patient.email, message)

    def test_admin_on_public_profile_is_not_logged(self):
        update_patient_profile(profile=self.profile, is_profile_public=True)
        with self.assertNoLogs("mindcare.audit", level="INFO"):
            self._identity(make_admin())
