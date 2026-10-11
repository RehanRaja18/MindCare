"""Service-layer tests for psychologists.

Per project convention, every new piece of business logic in services.py
gets a test here before the feature is considered done.
"""

from django.test import TestCase

from apps.accounts.models import Role
from apps.psychologists.services import (
    CredentialFieldLockedError,
    DuplicateLicenseError,
    create_psychologist_profile,
    update_psychologist_profile,
)
from apps.reference.models import City, Country, Specialization
from core.exceptions import DomainValidationError
from core.testing import make_user, psychologist_profile_data


def _create(**overrides):
    return create_psychologist_profile(
        user=make_user(role=Role.PSYCHOLOGIST), **psychologist_profile_data(**overrides)
    )


class CreatePsychologistProfileTests(TestCase):
    def test_creates_profile_with_m2m_and_normalized_license(self):
        profile = _create(license_number="  pmdc-777 ")
        self.assertEqual(profile.license_number, "PMDC-777")
        self.assertEqual(
            profile.city, City.objects.get(country__code="PK", name="Lahore")
        )
        self.assertEqual(profile.specializations.count(), 2)
        self.assertEqual(profile.languages.count(), 2)

    def test_duplicate_license_same_country_rejected_after_normalization(self):
        _create(license_number="PMDC-1")
        with self.assertRaises(DuplicateLicenseError) as ctx:
            _create(license_number=" pmdc-1")
        self.assertEqual(
            ctx.exception.errors,
            {"license_number": ["This license is already registered."]},
        )

    def test_same_license_number_in_another_country_allowed(self):
        _create(license_number="X-1")
        _create(
            license_number="X-1", license_issuing_country=Country.objects.get(code="GB")
        )

    def test_requires_at_least_one_specialization_and_language(self):
        with self.assertRaises(DomainValidationError):
            _create(specializations=[])
        with self.assertRaises(DomainValidationError):
            _create(languages=[])

    def test_inactive_specialization_rejected(self):
        Specialization.objects.filter(slug="anxiety").update(is_active=False)
        with self.assertRaises(DomainValidationError):
            _create(specializations=list(Specialization.objects.filter(slug="anxiety")))

    def test_rejects_non_psychologist_user(self):
        with self.assertRaises(ValueError):
            create_psychologist_profile(
                user=make_user(role=Role.PATIENT), **psychologist_profile_data()
            )

    def test_create_with_invalid_gender_raises_and_creates_no_profile(self):
        from apps.psychologists.models import PsychologistProfile

        with self.assertRaises(DomainValidationError) as ctx:
            _create(gender="alien")
        self.assertEqual(ctx.exception.errors, {"gender": ["Choose a valid option."]})
        self.assertEqual(PsychologistProfile.objects.count(), 0)

    def test_create_with_years_of_experience_above_max_rejected(self):
        from apps.psychologists.models import PsychologistProfile

        with self.assertRaises(DomainValidationError) as ctx:
            _create(years_of_experience=61)
        self.assertEqual(
            ctx.exception.errors,
            {
                "years_of_experience": [
                    "Years of experience must be a whole number between 0 and 60."
                ]
            },
        )
        self.assertEqual(PsychologistProfile.objects.count(), 0)

    def test_create_with_negative_years_of_experience_rejected(self):
        from apps.psychologists.models import PsychologistProfile

        with self.assertRaises(DomainValidationError) as ctx:
            _create(years_of_experience=-1)
        self.assertEqual(
            ctx.exception.errors,
            {
                "years_of_experience": [
                    "Years of experience must be a whole number between 0 and 60."
                ]
            },
        )
        self.assertEqual(PsychologistProfile.objects.count(), 0)

    def test_create_with_years_of_experience_boundaries_accepted(self):
        profile_low = _create(license_number="B-0", years_of_experience=0)
        self.assertEqual(profile_low.years_of_experience, 0)
        profile_high = _create(license_number="B-60", years_of_experience=60)
        self.assertEqual(profile_high.years_of_experience, 60)


class UpdatePsychologistProfileTests(TestCase):
    def setUp(self):
        self.profile = _create()

    def test_non_credential_fields_editable(self):
        update_psychologist_profile(
            profile=self.profile,
            bio="Hello, I work with adults on anxiety.",
            years_of_experience=6,
            specializations=list(Specialization.objects.filter(slug="grief")),
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "Hello, I work with adults on anxiety.")
        self.assertEqual(
            list(self.profile.specializations.values_list("slug", flat=True)), ["grief"]
        )

    def test_changed_credential_rejected(self):
        with self.assertRaises(CredentialFieldLockedError) as ctx:
            update_psychologist_profile(
                profile=self.profile, license_number="PMDC-99999"
            )
        self.assertEqual(ctx.exception.code, "credential_field_locked")
        self.assertIn("license_number", ctx.exception.errors)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.license_number, "PMDC-12345")

    def test_unchanged_credentials_accepted_on_full_object_patch(self):
        data = psychologist_profile_data(
            license_number=" pmdc-12345 ", bio="Updated bio about my clinical practice."
        )
        update_psychologist_profile(profile=self.profile, **data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "Updated bio about my clinical practice.")

    def test_every_credential_field_is_locked(self):
        changes = {
            "license_issuing_country": Country.objects.get(code="GB"),
            "license_issuing_authority": "Someone else",
            "qualifications": "PhD",
        }
        for field, value in changes.items():
            with self.assertRaises(CredentialFieldLockedError):
                update_psychologist_profile(profile=self.profile, **{field: value})

    def test_city_cannot_be_cleared(self):
        with self.assertRaises(DomainValidationError):
            update_psychologist_profile(profile=self.profile, city="")

    def test_update_with_invalid_gender_raises_and_leaves_value_unchanged(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_psychologist_profile(profile=self.profile, gender="alien")
        self.assertEqual(ctx.exception.errors, {"gender": ["Choose a valid option."]})
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.gender)

    def test_update_with_gender_none_clears_it(self):
        update_psychologist_profile(profile=self.profile, gender="male")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.gender, "male")

        update_psychologist_profile(profile=self.profile, gender=None)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.gender)

    def test_update_with_years_of_experience_above_max_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_psychologist_profile(profile=self.profile, years_of_experience=61)
        self.assertEqual(
            ctx.exception.errors,
            {
                "years_of_experience": [
                    "Years of experience must be a whole number between 0 and 60."
                ]
            },
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.years_of_experience, 5)
