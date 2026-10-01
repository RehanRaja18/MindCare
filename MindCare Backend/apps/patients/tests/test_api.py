"""API-layer tests for patients."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.patients.services import create_patient_profile
from core.testing import make_user

ME_URL = "/api/v1/patients/me/"


class PatientMeAPITests(APITestCase):
    def setUp(self):
        self.user = make_user(role=Role.PATIENT, full_name="Ayesha Khan")
        self.profile = create_patient_profile(user=self.user, timezone="Asia/Karachi")
        self.client.force_authenticate(self.user)

    def test_get_own_profile(self):
        r = self.client.get(ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["pseudonym"], self.profile.pseudonym)
        self.assertEqual(r.data["full_name"], "Ayesha Khan")
        self.assertFalse(r.data["is_profile_public"])

    def test_patch_updates_fields(self):
        r = self.client.patch(
            ME_URL,
            {"country": "PK", "city": "Lahore", "preferred_language": "ur"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data["city"]["name"], "Lahore")
        self.assertEqual(r.data["country"]["code"], "PK")
        self.assertEqual(r.data["preferred_language"]["code"], "ur")

    def test_patch_pseudonym_rejected(self):
        r = self.client.patch(ME_URL, {"pseudonym": "Patient-000000"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pseudonym", r.data)

    def test_patch_under_18_dob_rejected(self):
        r = self.client.patch(ME_URL, {"date_of_birth": "2020-01-01"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_of_birth", r.data)

    def test_other_roles_forbidden(self):
        self.client.force_authenticate(make_user(role=Role.PSYCHOLOGIST))
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_unauthorized(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(ME_URL).status_code, status.HTTP_401_UNAUTHORIZED
        )
