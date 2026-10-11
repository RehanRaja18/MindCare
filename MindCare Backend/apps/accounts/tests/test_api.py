"""API-layer tests for accounts."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import ApprovalStatus, Role, User
from core.testing import register_payload

REGISTER_URL = "/api/v1/accounts/register/"
LOGIN_URL = "/api/v1/accounts/login/"


class RegisterAPITests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_patient_can_register_and_is_approved(self):
        response = self.client.post(
            REGISTER_URL,
            register_payload(
                role="patient", email="newpatient@example.com", full_name="New Patient"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="newpatient@example.com")
        self.assertEqual(user.approval_status, ApprovalStatus.APPROVED)

    def test_psychologist_registration_is_pending(self):
        response = self.client.post(
            REGISTER_URL,
            register_payload(
                role="psychologist", email="newdoc@example.com", full_name="New Doc"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="newdoc@example.com")
        self.assertEqual(user.approval_status, ApprovalStatus.PENDING)

    def test_admin_role_is_rejected(self):
        payload = register_payload(role="patient", email="wannabeadmin@example.com")
        payload["role"] = "admin"
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="wannabeadmin@example.com").exists())

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="dup@example.com",
            password="strongpass123",
            full_name="Existing",
            role=Role.PATIENT,
        )
        response = self.client.post(
            REGISTER_URL,
            register_payload(
                role="patient", email="dup@example.com", full_name="Dup Attempt"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            REGISTER_URL,
            register_payload(
                role="patient",
                email="weakpass@example.com",
                password="password",
                full_name="Weak Password",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(email="weakpass@example.com").exists())

    def test_purely_numeric_weak_password_is_rejected(self):
        response = self.client.post(
            REGISTER_URL,
            register_payload(
                role="patient",
                email="numericpass@example.com",
                password="12345678",
                full_name="Numeric Password",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_endpoint_is_throttled_after_repeated_requests(self):
        for i in range(10):
            response = self.client.post(
                REGISTER_URL,
                register_payload(role="patient", email=f"throttleuser{i}@example.com"),
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            REGISTER_URL,
            register_payload(
                role="patient", email="throttleuser-over-limit@example.com"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class RegisterWithProfileAPITests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_psychologist_register_returns_profile(self):
        r = self.client.post(
            REGISTER_URL, register_payload(role="psychologist"), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["approval_status"], "pending")
        self.assertEqual(r.data["profile"]["license_number"], "PMDC-12345")

    def test_patient_register_returns_pseudonym(self):
        r = self.client.post(
            REGISTER_URL, register_payload(role="patient"), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertRegex(r.data["profile"]["pseudonym"], r"^Patient-[0-9a-f]{6}$")

    def test_adult_declaration_required(self):
        for value in (False, None):
            payload = register_payload(role="patient", is_adult_confirmed=value)
            r = self.client.post(REGISTER_URL, payload, format="json")
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("is_adult_confirmed", r.data)
            self.assertEqual(
                str(r.data["is_adult_confirmed"][0]),
                "You must confirm you are 18 or older.",
            )

    def test_is_adult_confirmed_only_accepts_json_boolean_true(self):
        """Truthy string values like "true", 1, "yes" must be rejected."""
        for value in ("true", 1, "yes"):
            with self.subTest(value=value):
                payload = register_payload(
                    role="patient",
                    email=f"truthy-{value}@example.com",
                    is_adult_confirmed=value,
                )
                r = self.client.post(REGISTER_URL, payload, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("is_adult_confirmed", r.data)
                self.assertFalse(User.objects.filter(email=payload["email"]).exists())

    def test_is_adult_confirmed_missing_key_rejected(self):
        """The is_adult_confirmed key must be present in the payload."""
        payload = register_payload(role="patient", email="nomissing@example.com")
        del payload["is_adult_confirmed"]
        r = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_adult_confirmed", r.data)
        self.assertEqual(
            str(r.data["is_adult_confirmed"][0]),
            "You must confirm you are 18 or older.",
        )
        self.assertFalse(User.objects.filter(email=payload["email"]).exists())

    def test_missing_psychologist_credentials_rejected_nothing_created(self):
        payload = register_payload(role="psychologist", email="nocreds@example.com")
        del payload["profile"]["license_number"]
        r = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("license_number", r.data["profile"])
        self.assertFalse(User.objects.filter(email="nocreds@example.com").exists())

    def test_unknown_profile_key_rejected(self):
        payload = register_payload(role="patient")
        payload["profile"]["pseudonym"] = "Patient-000000"
        r = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pseudonym", r.data["profile"])

    def test_ngo_unknown_service_area_key_rejected(self):
        payload = register_payload(role="ngo", email="typo@example.com")
        payload["profile"]["service_areas"] = [{"country": "PK", "cty": "Lahore"}]
        r = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="typo@example.com").exists())

    def test_duplicate_license_is_generic_400(self):
        self.client.post(
            REGISTER_URL, register_payload(role="psychologist"), format="json"
        )
        r = self.client.post(
            REGISTER_URL,
            register_payload(role="psychologist", email="second@example.com"),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            r.data["profile"]["license_number"], ["This license is already registered."]
        )
        self.assertFalse(User.objects.filter(email="second@example.com").exists())


class LoginAPITests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.password = "strongpass123"
        self.patient = User.objects.create_user(
            email="loginpatient@example.com",
            password=self.password,
            full_name="Pat Ient",
            role=Role.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.pending_psych = User.objects.create_user(
            email="loginpending@example.com",
            password=self.password,
            full_name="Pending Doc",
            role=Role.PSYCHOLOGIST,
            approval_status=ApprovalStatus.PENDING,
        )

    def test_successful_login_returns_tokens_with_role_claim(self):
        response = self.client.post(
            LOGIN_URL, {"email": "loginpatient@example.com", "password": self.password}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken(response.data["access"])
        self.assertEqual(token["role"], "patient")

    def test_pending_account_login_is_rejected_with_clear_message(self):
        response = self.client.post(
            LOGIN_URL, {"email": "loginpending@example.com", "password": self.password}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("pending admin approval", str(response.data))

    def test_wrong_password_rejected(self):
        response = self.client.post(
            LOGIN_URL, {"email": "loginpatient@example.com", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_endpoint_is_throttled_after_repeated_failures(self):
        for _ in range(5):
            self.client.post(
                LOGIN_URL,
                {"email": "loginpatient@example.com", "password": "wrongpass"},
            )
        response = self.client.post(
            LOGIN_URL, {"email": "loginpatient@example.com", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


REFRESH_URL = "/api/v1/accounts/refresh/"
LOGOUT_URL = "/api/v1/accounts/logout/"


class RefreshAndLogoutAPITests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.password = "strongpass123"
        self.user = User.objects.create_user(
            email="refreshuser@example.com",
            password=self.password,
            full_name="Refresh User",
            role=Role.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
        )
        login = self.client.post(
            LOGIN_URL, {"email": "refreshuser@example.com", "password": self.password}
        )
        self.access = login.data["access"]
        self.refresh = login.data["refresh"]

    def test_refresh_rotates_token_and_blacklists_old_one(self):
        response = self.client.post(REFRESH_URL, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_refresh = response.data["refresh"]
        self.assertNotEqual(new_refresh, self.refresh)

        reuse_response = self.client.post(REFRESH_URL, {"refresh": self.refresh})
        self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_is_rejected_after_approval_status_changes_to_pending(self):
        self.user.approval_status = ApprovalStatus.PENDING
        self.user.save(update_fields=["approval_status"])

        response = self.client.post(REFRESH_URL, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_is_rejected_after_account_is_rejected(self):
        self.user.approval_status = ApprovalStatus.REJECTED
        self.user.save(update_fields=["approval_status"])

        response = self.client.post(REFRESH_URL, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_authentication(self):
        response = self.client.post(LOGOUT_URL, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.post(LOGOUT_URL, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_after_logout = self.client.post(REFRESH_URL, {"refresh": self.refresh})
        self.assertEqual(refresh_after_logout.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_rejects_token_from_different_user(self):
        # Create another user and get their tokens
        User.objects.create_user(
            email="otheruser@example.com",
            password=self.password,
            full_name="Other User",
            role=Role.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
        )
        other_login = self.client.post(
            LOGIN_URL, {"email": "otheruser@example.com", "password": self.password}
        )
        other_refresh = other_login.data["refresh"]

        # First user tries to logout with other user's refresh token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.post(LOGOUT_URL, {"refresh": other_refresh})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not belong", str(response.data))

        # Verify other user's token is still valid (not blacklisted)
        refresh_result = self.client.post(REFRESH_URL, {"refresh": other_refresh})
        self.assertEqual(refresh_result.status_code, status.HTTP_200_OK)


class TemporaryDebugEndpointRemovedTests(APITestCase):
    """The NUM_PROXIES probe lived for exactly one PR (decisions.md, 2026-10-10)."""

    def test_client_ip_probe_is_gone(self):
        from core.testing import make_admin

        self.client.force_authenticate(make_admin())
        response = self.client.get("/api/v1/accounts/debug/client-ip/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
