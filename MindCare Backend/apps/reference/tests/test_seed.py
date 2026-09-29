"""The seed data migration loaded the expected reference rows."""

import json
from pathlib import Path

from django.test import TestCase

from apps.reference.models import City, Country, Language, Specialization

DATA = Path(__file__).resolve().parent.parent / "data"


def _load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


class SeedDataTests(TestCase):
    def test_all_iso_countries_seeded(self):
        self.assertEqual(Country.objects.count(), 249)
        self.assertEqual(len({c["code"] for c in _load("countries.json")}), 249)
        for code in ["PK", "GB", "US", "DE", "AE", "SA", "IN", "CN", "CA"]:
            self.assertTrue(Country.objects.filter(code=code).exists(), code)

    def test_turkey_uses_current_official_name(self):
        self.assertEqual(Country.objects.get(code="TR").name, "Türkiye")

    def test_seeded_pakistani_cities_are_verified(self):
        self.assertFalse(City.objects.filter(country__code="PK", is_verified=False))

    def test_languages_seeded_and_active(self):
        self.assertEqual(Language.objects.count(), 183)
        self.assertFalse(Language.objects.filter(code="bh").exists())
        for code in ["en", "ur", "ar", "pa", "ps", "sd", "fa", "hi", "zh"]:
            self.assertTrue(
                Language.objects.filter(code=code, is_active=True).exists(), code
            )

    def test_pakistani_cities_seeded(self):
        expected = _load("pakistan_cities.json")
        self.assertEqual(City.objects.filter(country__code="PK").count(), len(expected))
        self.assertTrue(City.objects.filter(country__code="PK", name="Lahore").exists())

    def test_placeholder_specializations_seeded(self):
        self.assertEqual(Specialization.objects.filter(is_active=True).count(), 12)
