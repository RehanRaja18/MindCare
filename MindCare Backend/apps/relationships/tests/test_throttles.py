"""Real throttle behaviour for the Phase 3 patient scopes, tied to the configured rates."""

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from core.testing import make_patient, make_psychologist

DIRECTORY = "/api/v1/psychologists/directory/"
REQUESTS = "/api/v1/relationships/requests/"


def _limit(scope):
    return int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope].split("/")[0])


class ThrottleTests(APITestCase):
    """DRF throttles store history in the default cache (LocMemCache in tests)."""

    def setUp(self):
        cache.clear()
        self.patient = make_patient()
        self.psych = make_psychologist()
        self.client.force_authenticate(self.patient.user)

    def tearDown(self):
        cache.clear()

    def test_relationship_requests_post_throttled_at_rate(self):
        limit = _limit("relationship_requests")
        body = {"psychologist": self.psych.pk}
        codes = [
            self.client.post(REQUESTS, body, format="json").status_code
            for _ in range(limit + 1)
        ]
        self.assertEqual(codes[0], status.HTTP_201_CREATED)
        # Later ones fail validation (already open) but still count: DRF throttles
        # before the handler runs.
        self.assertEqual(codes[1:limit], [status.HTTP_400_BAD_REQUEST] * (limit - 1))
        self.assertEqual(codes[limit], status.HTTP_429_TOO_MANY_REQUESTS)
        # Only POST is throttled.
        self.assertEqual(self.client.get(REQUESTS).status_code, status.HTTP_200_OK)

    def test_directory_throttled_at_rate_and_detail_shares_scope(self):
        limit = _limit("directory")
        codes = [self.client.get(DIRECTORY).status_code for _ in range(limit + 1)]
        self.assertEqual(codes[:limit], [status.HTTP_200_OK] * limit)
        self.assertEqual(codes[limit], status.HTTP_429_TOO_MANY_REQUESTS)
        detail = self.client.get(f"{DIRECTORY}{self.psych.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
