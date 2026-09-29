"""Service-layer tests for reference."""

from django.test import TestCase

from apps.reference.models import City, Country, Language
from apps.reference.services import (
    ensure_active_choices,
    resolve_city,
    resolve_location_fields,
)
from core.exceptions import DomainValidationError


class ResolveCityTests(TestCase):
    def setUp(self):
        self.pk = Country.objects.get(code="PK")
        self.gb = Country.objects.get(code="GB")

    def test_reuses_seeded_city_case_and_whitespace_insensitively(self):
        city = resolve_city(country=self.pk, name="  lahore ")
        self.assertEqual(city.name, "Lahore")
        self.assertEqual(
            City.objects.filter(country=self.pk, name__iexact="lahore").count(), 1
        )

    def test_new_city_is_unverified_and_seeded_city_stays_verified(self):
        created = resolve_city(country=self.gb, name="Leeds")
        self.assertFalse(created.is_verified)
        self.assertTrue(resolve_city(country=self.pk, name="lahore").is_verified)

    def test_creates_new_city_once(self):
        first = resolve_city(country=self.gb, name="london")
        second = resolve_city(country=self.gb, name="LONDON")
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.name, "london")

    def test_same_name_in_different_countries_is_distinct(self):
        a = resolve_city(country=self.pk, name="Hyderabad")
        b = resolve_city(country=Country.objects.get(code="IN"), name="Hyderabad")
        self.assertNotEqual(a.pk, b.pk)

    def test_blank_name_rejected(self):
        with self.assertRaises(DomainValidationError) as ctx:
            resolve_city(country=self.pk, name="   ")
        self.assertIn("city", ctx.exception.errors)

    def test_too_long_name_rejected(self):
        with self.assertRaises(DomainValidationError):
            resolve_city(country=self.pk, name="x" * 121)


class ResolveLocationFieldsTests(TestCase):
    def setUp(self):
        self.pk = Country.objects.get(code="PK")
        self.gb = Country.objects.get(code="GB")
        self.lahore = City.objects.get(country=self.pk, name="Lahore")

    def test_city_name_resolved_against_new_country(self):
        fields = resolve_location_fields(
            current_country=None,
            current_city=None,
            fields={"country": self.gb, "city": "Leeds"},
            city_required=False,
        )
        self.assertEqual(fields["city"].country, self.gb)

    def test_city_without_any_country_rejected(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=None,
                current_city=None,
                fields={"city": "Leeds"},
                city_required=False,
            )

    def test_country_cannot_be_cleared_once_set(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=self.pk,
                current_city=self.lahore,
                fields={"country": None},
                city_required=False,
            )

    def test_changing_country_clears_stale_optional_city(self):
        fields = resolve_location_fields(
            current_country=self.pk,
            current_city=self.lahore,
            fields={"country": self.gb},
            city_required=False,
        )
        self.assertIsNone(fields["city"])

    def test_changing_country_without_city_rejected_when_city_required(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=self.pk,
                current_city=self.lahore,
                fields={"country": self.gb},
                city_required=True,
            )

    def test_blank_city_rejected_when_required(self):
        with self.assertRaises(DomainValidationError):
            resolve_location_fields(
                current_country=self.pk,
                current_city=self.lahore,
                fields={"city": ""},
                city_required=True,
            )


class EnsureActiveChoicesTests(TestCase):
    def test_empty_rejected(self):
        with self.assertRaises(DomainValidationError):
            ensure_active_choices(items=[], field="languages")

    def test_inactive_rejected(self):
        lang = Language.objects.get(code="en")
        lang.is_active = False
        lang.save()
        with self.assertRaises(DomainValidationError):
            ensure_active_choices(items=[lang], field="languages")

    def test_active_passes(self):
        ensure_active_choices(
            items=[Language.objects.get(code="ur")], field="languages"
        )
