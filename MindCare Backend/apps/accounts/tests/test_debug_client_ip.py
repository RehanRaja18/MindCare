"""TEMPORARY: tests for the client-IP debug endpoint used to measure the proxy
hop count for NUM_PROXIES on Render. Delete together with the endpoint in the
very next PR (see docs/decisions.md, 2026-10-10)."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from core.testing import make_admin, make_user

URL = "/api/v1/accounts/debug/client-ip/"


class ClientIpDebugTests(APITestCase):
    def test_admin_sees_the_proxy_headers(self):
        self.client.force_authenticate(make_admin())
        response = self.client.get(
            URL,
            HTTP_X_FORWARDED_FOR="203.0.113.7, 172.70.1.1",
            HTTP_CF_CONNECTING_IP="203.0.113.7",
            HTTP_TRUE_CLIENT_IP="203.0.113.7",
            REMOTE_ADDR="10.0.0.5",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["remote_addr"], "10.0.0.5")
        self.assertEqual(response.data["x_forwarded_for"], "203.0.113.7, 172.70.1.1")
        self.assertEqual(response.data["x_forwarded_for_count"], 2)
        self.assertEqual(response.data["cf_connecting_ip"], "203.0.113.7")
        self.assertEqual(response.data["true_client_ip"], "203.0.113.7")
        self.assertIn("num_proxies", response.data)
        self.assertIn("throttle_ident", response.data)

    def test_missing_headers_are_null(self):
        self.client.force_authenticate(make_admin())
        response = self.client.get(URL, REMOTE_ADDR="10.0.0.5")
        self.assertIsNone(response.data["x_forwarded_for"])
        self.assertEqual(response.data["x_forwarded_for_count"], 0)
        self.assertIsNone(response.data["cf_connecting_ip"])

    def test_non_admins_are_refused(self):
        for role in (Role.PATIENT, Role.PSYCHOLOGIST, Role.NGO):
            self.client.force_authenticate(make_user(role=role))
            self.assertEqual(
                self.client.get(URL).status_code, status.HTTP_403_FORBIDDEN
            )

    def test_anonymous_is_refused(self):
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_401_UNAUTHORIZED)
