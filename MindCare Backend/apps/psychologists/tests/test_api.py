"""API-layer tests for psychologists."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.psychologists.services import create_psychologist_profile
from core.testing import (
    make_user,
    psychologist_profile_data,
    psychologist_profile_payload,
)

ME_URL = "/api/v1/psychologists/me/"


class PsychologistMeAPITests(APITestCase):
    def setUp(self):
        self.user = make_user(role=Role.PSYCHOLOGIST)
        create_psychologist_profile(user=self.user, **psychologist_profile_data())
        self.client.force_authenticate(self.user)

    def test_owner_sees_license_number(self):
        r = self.client.get(ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["license_number"], "PMDC-12345")
        self.assertEqual(r.data["license_issuing_country"]["code"], "PK")
        self.assertEqual(
            {s["slug"] for s in r.data["specializations"]}, {"anxiety", "depression"}
        )

    def test_patch_editable_fields(self):
        r = self.client.patch(
            ME_URL,
            {"bio": "Hi, I help adults with anxiety and stress.", "languages": ["en"]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual([lang["code"] for lang in r.data["languages"]], ["en"])

    def test_patch_changed_license_is_locked(self):
        r = self.client.patch(ME_URL, {"license_number": "NEW-1"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["license_number"][0].code, "credential_field_locked")

    def test_full_object_patch_with_unchanged_credentials_ok(self):
        r = self.client.patch(
            ME_URL,
            psychologist_profile_payload(
                bio="Same credentials, a longer bio for the rule."
            ),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_owner_still_sees_own_unverified_city(self):
        user = make_user(role=Role.PSYCHOLOGIST)
        create_psychologist_profile(
            user=user,
            **psychologist_profile_data(license_number="PMDC-99999", city="Newtown"),
        )
        self.client.force_authenticate(user)
        r = self.client.get(ME_URL)
        self.assertEqual(r.data["city"]["name"], "Newtown")

    def test_patient_forbidden(self):
        self.client.force_authenticate(make_user(role=Role.PATIENT))
        self.assertEqual(self.client.get(ME_URL).status_code, status.HTTP_403_FORBIDDEN)
