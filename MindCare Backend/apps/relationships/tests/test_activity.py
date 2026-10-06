"""Activity tracking: psychologists only, cached, never breaks auth."""

from unittest.mock import patch

from django.core.cache import cache
from django.db import DatabaseError
from django.db.models.query import QuerySet
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User
from apps.relationships.services import ACTIVITY_CACHE_SECONDS, record_activity
from core.testing import make_patient, make_psychologist


class RecordActivityTests(APITestCase):
    def setUp(self):
        # LocMemCache persists across tests in one process.
        cache.clear()
        self.psych = make_psychologist()

    def test_psychologist_written_once_per_window(self):
        record_activity(user=self.psych.user)
        first = User.objects.get(pk=self.psych.user.pk).last_active_at
        self.assertIsNotNone(first)
        with self.assertNumQueries(0):  # cache hit: no database write
            record_activity(user=self.psych.user)

    def test_other_roles_never_written(self):
        patient = make_patient()
        with patch("apps.relationships.services.cache") as fake_cache:
            record_activity(user=patient.user)
        fake_cache.add.assert_not_called()
        self.assertEqual(fake_cache.method_calls, [])
        self.assertIsNone(User.objects.get(pk=patient.user.pk).last_active_at)

    def test_cache_error_skips_silently(self):
        with patch("apps.relationships.services.cache") as fake_cache:
            fake_cache.add.side_effect = ConnectionError("redis down")
            record_activity(user=self.psych.user)  # no exception
        self.assertIsNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def _auth(self, user):
        token = RefreshToken.for_user(user)
        token["role"] = user.role
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return token

    def test_authenticated_request_records_activity(self):
        self._auth(self.psych.user)
        self.client.get("/api/v1/psychologists/me/")
        self.assertIsNotNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def test_logout_does_not_record_activity(self):
        refresh = self._auth(self.psych.user)
        self.client.post(
            "/api/v1/accounts/logout/", {"refresh": str(refresh)}, format="json"
        )
        self.assertIsNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def test_refresh_does_not_record_activity(self):
        # RefreshView sets authentication_classes = [], so the bearer header is
        # never authenticated there; UNTRACKED_PATHS also lists it as a backstop.
        refresh = self._auth(self.psych.user)
        response = self.client.post(
            "/api/v1/accounts/refresh/", {"refresh": str(refresh)}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def test_redis_outage_never_breaks_authentication(self):
        self._auth(self.psych.user)
        with patch("apps.relationships.services.cache") as fake_cache:
            fake_cache.add.side_effect = ConnectionError("redis down")
            response = self.client.get("/api/v1/psychologists/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.psych.user.role, Role.PSYCHOLOGIST)

    def test_database_error_skips_silently_and_clears_cache_key(self):
        with patch.object(QuerySet, "update", side_effect=DatabaseError("db down")):
            record_activity(user=self.psych.user)  # no exception
        self.assertIsNone(cache.get(f"last_active:{self.psych.user.pk}"))
        self.assertIsNone(User.objects.get(pk=self.psych.user.pk).last_active_at)

    def test_cache_key_lasts_one_window(self):
        with patch("apps.relationships.services.cache") as fake_cache:
            fake_cache.add.return_value = True
            record_activity(user=self.psych.user)
        fake_cache.add.assert_called_once_with(
            f"last_active:{self.psych.user.pk}", 1, ACTIVITY_CACHE_SECONDS
        )

    def test_database_error_never_breaks_authentication(self):
        self._auth(self.psych.user)
        with patch.object(QuerySet, "update", side_effect=DatabaseError("db down")):
            response = self.client.get("/api/v1/psychologists/me/")
        self.assertEqual(response.status_code, 200)
