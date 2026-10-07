"""Service-layer tests for patients.

Per project convention, every new piece of business logic in services.py
gets a test here before the feature is considered done.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone as dj_timezone

from apps.accounts.models import Role
from apps.patients.services import (
    PseudonymGenerationError,
    create_patient_profile,
    update_patient_profile,
)
from apps.reference.models import City, Country, Language
from core.exceptions import DomainValidationError
from core.testing import make_user


def _eighteenth_birthday_today():
    today = dj_timezone.localdate()
    try:
        return today.replace(year=today.year - 18)
    except ValueError:  # today is Feb 29
        return today.replace(year=today.year - 18, day=28)


class CreatePatientProfileTests(TestCase):
    def test_creates_profile_with_pseudonym_and_private_default(self):
        profile = create_patient_profile(
            user=make_user(role=Role.PATIENT), timezone="Asia/Karachi"
        )
        self.assertRegex(profile.pseudonym, r"^Patient-[0-9a-f]{6}$")
        self.assertFalse(profile.is_profile_public)
        self.assertEqual(profile.timezone, "Asia/Karachi")

    def test_rejects_non_patient_user(self):
        with self.assertRaises(ValueError):
            create_patient_profile(
                user=make_user(role=Role.PSYCHOLOGIST), timezone="UTC"
            )

    def test_rejects_invalid_timezone(self):
        with self.assertRaises(DomainValidationError):
            create_patient_profile(
                user=make_user(role=Role.PATIENT), timezone="Mars/Base"
            )

    def test_retries_on_pseudonym_collision(self):
        first = create_patient_profile(
            user=make_user(role=Role.PATIENT), timezone="UTC"
        )
        with patch(
            "apps.patients.services.generate_pseudonym",
            side_effect=[first.pseudonym, "Patient-abcdef"],
        ):
            second = create_patient_profile(
                user=make_user(role=Role.PATIENT), timezone="UTC"
            )
        self.assertEqual(second.pseudonym, "Patient-abcdef")

    def test_gives_up_after_five_collisions(self):
        first = create_patient_profile(
            user=make_user(role=Role.PATIENT), timezone="UTC"
        )
        with patch(
            "apps.patients.services.generate_pseudonym", return_value=first.pseudonym
        ):
            with self.assertRaises(PseudonymGenerationError):
                create_patient_profile(
                    user=make_user(role=Role.PATIENT), timezone="UTC"
                )


class UpdatePatientProfileTests(TestCase):
    def setUp(self):
        self.profile = create_patient_profile(
            user=make_user(role=Role.PATIENT), timezone="Asia/Karachi"
        )
        self.pk = Country.objects.get(code="PK")
        self.gb = Country.objects.get(code="GB")

    def test_updates_location_and_preferences(self):
        update_patient_profile(
            profile=self.profile,
            country=self.pk,
            city="lahore",
            gender="female",
            phone_number="+923001234567",
            preferred_language=Language.objects.get(code="ur"),
            is_profile_public=True,
        )
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.city, City.objects.get(country=self.pk, name="Lahore")
        )
        self.assertTrue(self.profile.is_profile_public)

    def test_pseudonym_never_changes(self):
        original = self.profile.pseudonym
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, pseudonym="Patient-000000")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.pseudonym, original)

    def test_dob_exactly_18_accepted_one_day_short_rejected(self):
        birthday = _eighteenth_birthday_today()
        update_patient_profile(profile=self.profile, date_of_birth=birthday)
        with self.assertRaises(DomainValidationError) as ctx:
            update_patient_profile(
                profile=self.profile, date_of_birth=birthday + timedelta(days=1)
            )
        self.assertIn("date_of_birth", ctx.exception.errors)

    def test_dob_can_be_corrected_but_not_cleared(self):
        from datetime import date

        update_patient_profile(profile=self.profile, date_of_birth=date(1990, 5, 5))
        update_patient_profile(profile=self.profile, date_of_birth=date(1991, 6, 6))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.date_of_birth, date(1991, 6, 6))
        with self.assertRaises(DomainValidationError) as ctx:
            update_patient_profile(profile=self.profile, date_of_birth=None)
        self.assertEqual(
            ctx.exception.errors,
            {"date_of_birth": ["Your date of birth can't be removed once set."]},
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.date_of_birth, date(1991, 6, 6))

    def test_dob_none_is_fine_when_never_set(self):
        update_patient_profile(profile=self.profile, date_of_birth=None)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.date_of_birth)

    def test_city_without_country_rejected(self):
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, city="Lahore")

    def test_changing_country_clears_stale_city(self):
        update_patient_profile(profile=self.profile, country=self.pk, city="Lahore")
        profile = update_patient_profile(profile=self.profile, country=self.gb)
        self.assertIsNone(profile.city)

    def test_invalid_phone_rejected(self):
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, phone_number="03001234567")

    def test_unknown_field_rejected(self):
        with self.assertRaises(DomainValidationError):
            update_patient_profile(profile=self.profile, diagnosis="x")

    def test_invalid_gender_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_patient_profile(profile=self.profile, gender="not-a-real-value")
        self.assertIn("gender", ctx.exception.errors)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.gender)

    def test_gender_can_be_cleared(self):
        update_patient_profile(profile=self.profile, gender="female")
        update_patient_profile(profile=self.profile, gender=None)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.gender)
