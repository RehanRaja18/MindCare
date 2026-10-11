"""API-layer tests for ngo."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.ngo.services import create_ngo_profile
from core.testing import make_user, ngo_profile_data, ngo_profile_payload

ME_URL = "/api/v1/ngo/me/"


class NGOMeAPITests(APITestCase):
    def setUp(self):
        self.user = make_user(role=Role.NGO)
        create_ngo_profile(user=self.user, **ngo_profile_data())
        self.client.force_authenticate(self.user)

    def test_owner_view_includes_admin_only_fields_and_areas(self):
        r = self.client.get(ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["registration_number"], "SECP-0001")
        self.assertEqual(
            r.data["service_areas"],
            [{"country": {"code": "PK", "name": "Pakistan"}, "city": None}],
        )

    def test_patch_replaces_service_areas(self):
        r = self.client.patch(
            ME_URL,
            {"service_areas": [{"country": "GB", "city": "Leeds"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data["service_areas"][0]["city"]["name"], "Leeds")

    def test_patch_empty_service_areas_rejected(self):
        r = self.client.patch(ME_URL, {"service_areas": []}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_malformed_service_areas_rejected_and_unchanged(self):
        for areas in ([{}], [{"city": "Leeds"}]):
            with self.subTest(areas=areas):
                r = self.client.patch(ME_URL, {"service_areas": areas}, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                stored = self.client.get(ME_URL).data["service_areas"]
                self.assertEqual(len(stored), 1)
                self.assertIsNone(stored[0]["city"])

    def test_patch_service_area_unknown_key_rejected_and_unchanged(self):
        r = self.client.patch(
            ME_URL,
            {"service_areas": [{"country": "PK", "cty": "Lahore"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cty", r.data["service_areas"][0])
        stored = self.client.get(ME_URL).data["service_areas"]
        self.assertEqual(len(stored), 1)
        self.assertIsNone(stored[0]["city"])

    def test_patch_service_area_without_country_fails_in_serializer(self):
        for areas in ([{}], [{"city": "Leeds"}]):
            with self.subTest(areas=areas):
                r = self.client.patch(ME_URL, {"service_areas": areas}, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("country", r.data["service_areas"][0])
                stored = self.client.get(ME_URL).data["service_areas"]
                self.assertEqual(len(stored), 1)
                self.assertIsNone(stored[0]["city"])

    def test_changed_registration_number_locked(self):
        r = self.client.patch(ME_URL, {"registration_number": "NEW-1"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            r.data["registration_number"][0].code, "credential_field_locked"
        )

    def test_full_object_patch_ok(self):
        r = self.client.patch(
            ME_URL,
            ngo_profile_payload(
                description="We support families through crisis counselling."
            ),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_invalid_email_rejected(self):
        r = self.client.patch(ME_URL, {"official_email": "bad"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patient_forbidden(self):
        self.client.force_authenticate(make_user(role=Role.PATIENT))
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)
