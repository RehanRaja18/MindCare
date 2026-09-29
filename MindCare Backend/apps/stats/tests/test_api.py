"""API tests for the public stats endpoint (contract used by MindCare Web)."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

URL = "/api/v1/stats/public/"


class PublicStatsAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_unauthenticated_and_exact_contract(self):
        r = self.client.get(URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(r.data), {"people_in_care", "verified_therapists", "cities"}
        )
        self.assertTrue(all(isinstance(v, int) for v in r.data.values()))

    def test_invalid_token_ignored(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer junk")
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_200_OK)

    def test_throttle_scope(self):
        from apps.stats.api.views import PublicStatsView

        self.assertEqual(PublicStatsView.throttle_classes[0].scope, "public_stats")
