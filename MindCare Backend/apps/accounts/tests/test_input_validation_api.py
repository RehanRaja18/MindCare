"""Every existing input field rejects bad values through the API with the exact
messages in docs/validation-rules.md (the input-validation-hardening retrofit)."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from core.testing import (
    make_patient,
    make_psychologist,
    make_user,
    ngo_profile_data,
    register_payload,
)

REGISTER_URL = "/api/v1/accounts/register/"

NAME_CHARS = (
    "{} can only contain letters, spaces, hyphens (-), apostrophes (') and dots (.)."
)
ORG_CHARS = "{} can only contain letters, numbers, spaces and & , . ' - ( ) /"
ID_CHARS = (
    "{} can only contain letters, numbers, spaces, dots (.), slashes (/) and "
    "hyphens (-)."
)
PHONE = (
    "Enter a phone number in international format (e.g. +923001234567), "
    "or a Pakistani number starting with 0 (e.g. 03001234567)."
)


class RegisterValidationTests(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def post(self, role, **overrides):
        cache.clear()  # register is throttled at 10/hour per address
        profile = overrides.pop("profile", {})
        payload = register_payload(role=role, **overrides)
        payload["profile"].update(profile)
        return self.client.post(REGISTER_URL, payload, format="json")

    def test_full_name_rules_for_every_role(self):
        bad = {
            "Sara Ahmed 2": NAME_CHARS.format("Full name"),
            "<script>alert(1)</script>": NAME_CHARS.format("Full name"),
            "   ": "This field may not be blank.",
            "A": "Full name must be between 2 and 100 characters.",
            "A" * 101: "Full name must be between 2 and 100 characters.",
        }
        for role in (Role.PATIENT, Role.PSYCHOLOGIST, Role.NGO):
            for value, message in bad.items():
                with self.subTest(role=role, value=value[:20]):
                    r = self.post(role, full_name=value)
                    self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(r.json()["full_name"], [message])

    def test_full_name_is_normalised_and_urdu_accepted(self):
        r = self.post(Role.PATIENT, full_name="  محمد   بلال  ")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.json())
        self.assertEqual(r.json()["full_name"], "محمد بلال")

    def test_password_too_similar_to_email_rejected(self):
        r = self.post(
            Role.PATIENT, email="zarmeena.khan@example.com", password="zarmeenakhan"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("too similar", r.json()["password"][0])

    def test_password_numeric_and_short_rejected(self):
        r = self.post(Role.PATIENT, password="1234")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "This password is too short. It must contain at least 8 characters.",
            r.json()["password"],
        )

    def test_psychologist_profile_fields(self):
        cases = {
            "license_number": ("PMDC#1", ID_CHARS.format("License number")),
            "license_issuing_authority": (
                "<b>PMDC</b>",
                ORG_CHARS.format("Issuing authority"),
            ),
            "qualifications": (
                "MS",
                "Qualifications must be between 10 and 1000 characters.",
            ),
            "years_of_experience": (
                61,
                "Years of experience must be a whole number between 0 and 60.",
            ),
            "city": ("Lahore 54000", NAME_CHARS.format("City")),
            "bio": ("Too short", "Bio must be between 30 and 2000 characters."),
        }
        for field, (value, message) in cases.items():
            with self.subTest(field=field):
                r = self.post(Role.PSYCHOLOGIST, profile={field: value})
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(r.json()["profile"][field], [message])
        self.assertFalse(User.objects.filter(role=Role.PSYCHOLOGIST).exists())

    def test_psychologist_bio_with_html_rejected(self):
        r = self.post(
            Role.PSYCHOLOGIST,
            profile={"bio": "I help adults <script>steal()</script> with anxiety."},
        )
        self.assertEqual(r.json()["profile"]["bio"], ["Bio can't contain HTML tags."])

    def test_psychologist_license_normalised(self):
        r = self.post(Role.PSYCHOLOGIST, profile={"license_number": "  pmdc-  777 "})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.json())
        self.assertEqual(r.json()["profile"]["license_number"], "PMDC- 777")

    def test_ngo_profile_fields(self):
        cases = {
            "organization_name": ("Help!!", ORG_CHARS.format("Organisation name")),
            "registration_number": (
                "SECP",
                "Registration number must contain at least one number.",
            ),
            "registering_authority": (
                "@SECP",
                ORG_CHARS.format("Registering authority"),
            ),
            "official_phone": ("12345", PHONE),
            "website": (
                "http://edhi.org",
                "Website must be a full https:// address (e.g. https://example.org).",
            ),
            "description": (
                "Short",
                "Description must be between 30 and 2000 characters.",
            ),
        }
        for field, (value, message) in cases.items():
            with self.subTest(field=field):
                r = self.post(Role.NGO, profile={field: value})
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(r.json()["profile"][field], [message])

    def test_ngo_real_names_and_local_phone_accepted(self):
        r = self.post(
            Role.NGO,
            profile={
                "organization_name": "Rescue 1122 (Punjab)",
                "registering_authority": "Pakistan Medical & Dental Council",
                "official_phone": "042 3578-1234",
                "website": "https://rescue.gov.pk",
            },
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.json())
        user = User.objects.get(email=r.json()["email"])
        self.assertEqual(user.ngo_profile.official_phone, "+924235781234")


class PatientProfileValidationTests(APITestCase):
    URL = "/api/v1/patients/me/"

    def setUp(self):
        self.profile = make_patient()
        self.client.force_authenticate(self.profile.user)

    def test_local_phone_normalised(self):
        r = self.client.patch(self.URL, {"phone_number": "0300-1234567"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.json())
        self.assertEqual(r.json()["phone_number"], "+923001234567")

    def test_bad_phone_and_city_rejected(self):
        r = self.client.patch(self.URL, {"phone_number": "call me"}, format="json")
        self.assertEqual(r.json(), {"phone_number": [PHONE]})
        r = self.client.patch(
            self.URL, {"country": "PK", "city": "<img src=x>"}, format="json"
        )
        self.assertEqual(r.json(), {"city": [NAME_CHARS.format("City")]})

    def test_unrealistic_date_of_birth_rejected(self):
        r = self.client.patch(self.URL, {"date_of_birth": "1890-01-01"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            r.json()["date_of_birth"],
            ["Enter a real date of birth (age 120 or under)."],
        )


class PsychologistProfileValidationTests(APITestCase):
    URL = "/api/v1/psychologists/me/"

    def setUp(self):
        self.profile = make_psychologist()
        self.client.force_authenticate(self.profile.user)

    def test_bio_and_years_rules(self):
        r = self.client.patch(self.URL, {"bio": "!!!!!!!!!!" * 4}, format="json")
        self.assertEqual(r.json(), {"bio": ["Bio must contain at least 3 letters."]})
        r = self.client.patch(self.URL, {"years_of_experience": -1}, format="json")
        self.assertEqual(
            r.json(),
            {
                "years_of_experience": [
                    "Years of experience must be a whole number between 0 and 60."
                ]
            },
        )

    def test_bio_can_be_cleared(self):
        r = self.client.patch(self.URL, {"bio": ""}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.json())


class NGOProfileValidationTests(APITestCase):
    URL = "/api/v1/ngo/me/"

    def setUp(self):
        from apps.ngo.services import create_ngo_profile

        user = make_user(role=Role.NGO)
        create_ngo_profile(user=user, **ngo_profile_data())
        self.client.force_authenticate(user)

    def test_contact_fields(self):
        r = self.client.patch(self.URL, {"official_phone": "phone"}, format="json")
        self.assertEqual(r.json(), {"official_phone": [PHONE]})
        r = self.client.patch(
            self.URL, {"website": "javascript:alert(1)"}, format="json"
        )
        self.assertEqual(
            r.json(),
            {
                "website": [
                    "Website must be a full https:// address (e.g. https://example.org)."
                ]
            },
        )

    def test_service_area_city_rule(self):
        r = self.client.patch(
            self.URL,
            {"service_areas": [{"country": "PK", "city": "Karachi #1"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        # The NGO view reports list items keyed by their index.
        self.assertEqual(
            r.json(), {"service_areas": {"0": {"city": [NAME_CHARS.format("City")]}}}
        )
