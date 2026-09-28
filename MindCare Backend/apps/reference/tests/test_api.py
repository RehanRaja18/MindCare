"""API-layer tests for reference (all public, read-only)."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

BASE = "/api/v1/reference"


class ReferenceAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_countries_public(self):
        r = self.client.get(f"{BASE}/countries/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn({"code": "PK", "name": "Pakistan"}, r.data)

    def test_cities_requires_country(self):
        self.assertEqual(
            self.client.get(f"{BASE}/cities/").status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_cities_search(self):
        r = self.client.get(f"{BASE}/cities/", {"country": "PK", "search": "lah"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data[0]["name"], "Lahore")
        self.assertEqual(r.data[0]["country"], "PK")
        self.assertIn("id", r.data[0])

    def test_languages_and_specializations_public(self):
        langs = self.client.get(f"{BASE}/languages/")
        specs = self.client.get(f"{BASE}/specializations/")
        self.assertEqual(langs.status_code, status.HTTP_200_OK)
        self.assertEqual(specs.status_code, status.HTTP_200_OK)
        self.assertIn("anxiety", [s["slug"] for s in specs.data])

    def test_invalid_bearer_token_does_not_block_public_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(
            self.client.get(f"{BASE}/countries/").status_code, status.HTTP_200_OK
        )

    def test_no_write_methods(self):
        r = self.client.post(
            f"{BASE}/cities/", {"country": "PK", "name": "X"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
