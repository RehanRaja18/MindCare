"""Selector tests for reference."""

from django.test import TestCase

from apps.reference.models import Language
from apps.reference.selectors import (
    list_languages,
    list_specializations,
    search_cities,
)


class SearchCitiesTests(TestCase):
    def test_prefix_search_case_insensitive_and_scoped_to_country(self):
        names = [c.name for c in search_cities(country_code="pk", search="la")]
        self.assertIn("Lahore", names)
        self.assertIn("Larkana", names)
        self.assertNotIn("Islamabad", names)

    def test_limit(self):
        self.assertEqual(len(search_cities(country_code="PK", limit=5)), 5)


class ActiveListTests(TestCase):
    def test_inactive_language_hidden(self):
        Language.objects.filter(code="en").update(is_active=False)
        self.assertNotIn("en", [lang.code for lang in list_languages()])

    def test_specializations_listed(self):
        self.assertEqual(len(list_specializations()), 12)
