"""Service-layer tests for ngo.

Per project convention, every new piece of business logic in services.py
gets a test here before the feature is considered done.
"""

from django.test import TestCase

from apps.accounts.models import Role
from apps.ngo.models import NGOProfile
from apps.ngo.services import (
    CredentialFieldLockedError,
    DuplicateNGORegistrationError,
    create_ngo_profile,
    update_ngo_profile,
)
from apps.reference.models import City, Country
from core.exceptions import DomainValidationError
from core.testing import make_user, ngo_profile_data


def _create(**overrides):
    return create_ngo_profile(
        user=make_user(role=Role.NGO), **ngo_profile_data(**overrides)
    )


class CreateNGOProfileTests(TestCase):
    def test_creates_profile_and_nationwide_service_area(self):
        profile = _create(registration_number=" secp-9 ")
        self.assertEqual(profile.registration_number, "SECP-9")
        area = profile.service_areas.get()
        self.assertEqual(area.country.code, "PK")
        self.assertIsNone(area.city)

    def test_city_and_nationwide_areas_in_different_countries(self):
        gb = Country.objects.get(code="GB")
        profile = _create(
            service_areas=[
                {"country": Country.objects.get(code="PK"), "city": None},
                {"country": gb, "city": "london"},
            ]
        )
        self.assertEqual(profile.service_areas.count(), 2)
        self.assertEqual(profile.service_areas.get(country=gb).city.name, "london")

    def test_requires_at_least_one_service_area(self):
        with self.assertRaises(DomainValidationError):
            _create(service_areas=[])

    def test_duplicate_service_areas_rejected(self):
        pk = Country.objects.get(code="PK")
        with self.assertRaises(DomainValidationError):
            _create(
                service_areas=[
                    {"country": pk, "city": "Lahore"},
                    {"country": pk, "city": "lahore"},
                ]
            )

    def test_duplicate_registration_rejected_generically(self):
        _create(registration_number="SECP-1")
        with self.assertRaises(DuplicateNGORegistrationError) as ctx:
            _create(registration_number="secp-1")
        self.assertEqual(
            ctx.exception.errors,
            {
                "registration_number": [
                    "This organisation registration is already on file."
                ]
            },
        )

    def test_invalid_email_rejected_and_no_profile_created(self):
        with self.assertRaises(DomainValidationError) as ctx:
            _create(official_email="not-an-email")
        self.assertIn("official_email", ctx.exception.errors)
        self.assertEqual(NGOProfile.objects.count(), 0)

    def test_blank_email_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            _create(official_email="")
        self.assertIn("official_email", ctx.exception.errors)

    def test_invalid_website_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            _create(website="not a url")
        self.assertIn("website", ctx.exception.errors)
        self.assertEqual(NGOProfile.objects.count(), 0)

    def test_blank_or_none_website_stored_as_empty_string(self):
        self.assertEqual(_create(website="").website, "")
        self.assertEqual(_create(registration_number="B-2", website=None).website, "")

    def test_over_long_fields_rejected(self):
        cases = {
            "description": "x" * 2001,
            "organization_name": "x" * 201,
            "registering_authority": "x" * 201,
            "registration_number": "x" * 65,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                with self.assertRaises(DomainValidationError) as ctx:
                    _create(**{field: value})
                self.assertIn(field, ctx.exception.errors)
        self.assertEqual(NGOProfile.objects.count(), 0)

    def test_over_long_email_and_website_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            _create(official_email="a" * 250 + "@x.org")
        self.assertIn("official_email", ctx.exception.errors)
        with self.assertRaises(DomainValidationError) as ctx:
            _create(website="https://example.org/" + "a" * 200)
        self.assertIn("website", ctx.exception.errors)
        self.assertEqual(NGOProfile.objects.count(), 0)

    def test_service_area_without_country_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            _create(service_areas=[{"city": "Leeds"}])
        self.assertIn("service_areas", ctx.exception.errors)

    def test_failed_create_leaves_no_orphan_city(self):
        gb = Country.objects.get(code="GB")
        with self.assertRaises(DomainValidationError):
            _create(
                official_email="bad",
                service_areas=[{"country": gb, "city": "Brand New Town"}],
            )
        self.assertFalse(City.objects.filter(name__iexact="Brand New Town").exists())

    def test_create_official_email_lowercased(self):
        profile = _create(
            registration_number="SECP-999",
            official_email="  Contact@HelpingHands.Example ",
        )
        self.assertEqual(profile.official_email, "contact@helpinghands.example")

    def test_duplicate_registration_leaves_no_orphan_city(self):
        _create(registration_number="SECP-7")
        gb = Country.objects.get(code="GB")
        with self.assertRaises(DuplicateNGORegistrationError):
            _create(
                registration_number="SECP-7",
                service_areas=[{"country": gb, "city": "Brand New Town"}],
            )
        self.assertFalse(City.objects.filter(name__iexact="Brand New Town").exists())


class UpdateNGOProfileTests(TestCase):
    def setUp(self):
        self.profile = _create()

    def test_service_areas_replaced(self):
        pk = Country.objects.get(code="PK")
        update_ngo_profile(
            profile=self.profile, service_areas=[{"country": pk, "city": "Quetta"}]
        )
        self.assertEqual(
            list(self.profile.service_areas.values_list("city__name", flat=True)),
            ["Quetta"],
        )

    def test_changed_credential_locked(self):
        with self.assertRaises(CredentialFieldLockedError) as ctx:
            update_ngo_profile(profile=self.profile, organization_name="Renamed Org")
        self.assertEqual(ctx.exception.code, "credential_field_locked")

    def test_unchanged_credentials_accepted(self):
        update_ngo_profile(
            profile=self.profile,
            **ngo_profile_data(description="Updated description of the organisation."),
        )
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.description, "Updated description of the organisation."
        )

    def test_normalized_equal_credentials_accepted(self):
        profile = update_ngo_profile(
            profile=self.profile,
            registration_number=" secp-0001 ",
            organization_name="Helping   Hands Foundation",
            description="Updated description of the organisation.",
        )
        self.assertEqual(
            profile.description, "Updated description of the organisation."
        )
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.description, "Updated description of the organisation."
        )
        self.assertEqual(self.profile.registration_number, "SECP-0001")
        self.assertEqual(self.profile.organization_name, "Helping Hands Foundation")

    def test_invalid_email_rejected_and_stored_value_unchanged(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_ngo_profile(profile=self.profile, official_email="bad")
        self.assertIn("official_email", ctx.exception.errors)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.official_email, "contact@helpinghands.example")

    def test_email_cannot_be_blanked(self):
        with self.assertRaises(DomainValidationError):
            update_ngo_profile(profile=self.profile, official_email="")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.official_email, "contact@helpinghands.example")

    def test_invalid_website_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_ngo_profile(profile=self.profile, website="nope")
        self.assertIn("website", ctx.exception.errors)

    def test_blank_website_stored_as_empty_string(self):
        update_ngo_profile(profile=self.profile, website="https://example.org")
        update_ngo_profile(profile=self.profile, website=None)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.website, "")

    def test_over_long_description_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_ngo_profile(profile=self.profile, description="x" * 2001)
        self.assertIn("description", ctx.exception.errors)

    def test_duplicate_service_areas_rejected_and_set_unchanged(self):
        pk = Country.objects.get(code="PK")
        with self.assertRaises(DomainValidationError):
            update_ngo_profile(
                profile=self.profile,
                service_areas=[
                    {"country": pk, "city": "Lahore"},
                    {"country": pk, "city": "lahore"},
                ],
            )
        self.assertIsNone(self.profile.service_areas.get().city)

    def test_over_long_email_and_website_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_ngo_profile(
                profile=self.profile, official_email="a" * 250 + "@x.org"
            )
        self.assertIn("official_email", ctx.exception.errors)
        with self.assertRaises(DomainValidationError) as ctx:
            update_ngo_profile(
                profile=self.profile, website="https://example.org/" + "a" * 200
            )
        self.assertIn("website", ctx.exception.errors)

    def test_service_area_without_country_rejected(self):
        with self.assertRaises(DomainValidationError):
            update_ngo_profile(profile=self.profile, service_areas=[{"city": "Leeds"}])
        self.assertIsNone(self.profile.service_areas.get().city)

    def test_failed_update_leaves_no_orphan_city(self):
        gb = Country.objects.get(code="GB")
        with self.assertRaises(DomainValidationError):
            update_ngo_profile(
                profile=self.profile,
                city="Another New Town",
                service_areas=[
                    {"country": gb, "city": "Brand New Town"},
                    {"country": gb, "city": "brand new town"},
                ],
            )
        self.assertFalse(City.objects.filter(name__iexact="Brand New Town").exists())
        self.assertFalse(City.objects.filter(name__iexact="Another New Town").exists())

    def test_update_official_email_lowercased(self):
        update_ngo_profile(profile=self.profile, official_email="NEW@Example.ORG")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.official_email, "new@example.org")

    def test_update_official_email_whitespace_only_rejected_unchanged(self):
        with self.assertRaises(DomainValidationError) as ctx:
            update_ngo_profile(profile=self.profile, official_email="   ")
        self.assertIn("official_email", ctx.exception.errors)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.official_email, "contact@helpinghands.example")
