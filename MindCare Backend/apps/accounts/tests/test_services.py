"""Service-layer tests for accounts.

Per project convention, every new piece of business logic in services.py
gets a test here before the feature is considered done.
"""

from django.test import TestCase

from apps.accounts.models import ApprovalStatus, Role, User
from apps.accounts.services import register_user
from core.audit import log_auth_event
from core.testing import (
    PATIENT_PROFILE_DATA,
    ngo_profile_data,
    psychologist_profile_data,
)


class UserManagerTests(TestCase):
    def test_create_user_sets_given_fields(self):
        user = User.objects.create_user(
            email="patient@example.com",
            password="strongpass123",
            full_name="Pat Ient",
            role=Role.PATIENT,
        )
        self.assertEqual(user.email, "patient@example.com")
        self.assertEqual(user.full_name, "Pat Ient")
        self.assertEqual(user.role, Role.PATIENT)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_super_admin)
        self.assertTrue(user.check_password("strongpass123"))

    def test_create_user_normalizes_email_domain(self):
        user = User.objects.create_user(
            email="patient@EXAMPLE.com",
            password="strongpass123",
            full_name="Pat Ient",
            role=Role.PATIENT,
        )
        self.assertEqual(user.email, "patient@example.com")

    def test_create_superuser_is_admin_and_super_admin(self):
        user = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.assertEqual(user.role, Role.ADMIN)
        self.assertEqual(user.approval_status, ApprovalStatus.APPROVED)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_super_admin)

    def test_create_superuser_forces_admin_role_even_if_overridden(self):
        user = User.objects.create_superuser(
            email="root2@example.com", password="strongpass123", role=Role.PATIENT
        )
        self.assertEqual(user.role, Role.ADMIN)


class LogAuthEventTests(TestCase):
    def test_login_event_is_logged_as_json_with_expected_fields(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            log_auth_event(
                "login",
                user_id=42,
                email="patient@example.com",
                role="patient",
                ip="127.0.0.1",
            )
        self.assertEqual(len(captured.output), 1)
        import json

        payload = json.loads(captured.records[0].getMessage())
        self.assertEqual(payload["event_type"], "login")
        self.assertEqual(payload["user_id"], 42)
        self.assertEqual(payload["email"], "patient@example.com")
        self.assertEqual(payload["role"], "patient")
        self.assertEqual(payload["ip"], "127.0.0.1")
        self.assertTrue(payload["success"])

    def test_failed_login_event_records_success_false(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            log_auth_event("login_failed", email="nobody@example.com", success=False)
        payload = __import__("json").loads(captured.records[0].getMessage())
        self.assertFalse(payload["success"])

    def test_unknown_event_type_raises(self):
        with self.assertRaises(ValueError):
            log_auth_event("not_a_real_event")


class RegisterUserTests(TestCase):
    def test_patient_registration_is_immediately_approved(self):
        user = register_user(
            email="newpatient@example.com",
            password="strongpass123",
            full_name="New Patient",
            role=Role.PATIENT,
            is_adult_confirmed=True,
            profile_data=dict(PATIENT_PROFILE_DATA),
        )
        self.assertEqual(user.approval_status, ApprovalStatus.APPROVED)

    def test_psychologist_registration_is_pending(self):
        user = register_user(
            email="newdoc@example.com",
            password="strongpass123",
            full_name="New Doc",
            role=Role.PSYCHOLOGIST,
            is_adult_confirmed=True,
            profile_data=psychologist_profile_data(),
        )
        self.assertEqual(user.approval_status, ApprovalStatus.PENDING)

    def test_ngo_registration_is_pending(self):
        user = register_user(
            email="newngo@example.com",
            password="strongpass123",
            full_name="New NGO",
            role=Role.NGO,
            is_adult_confirmed=True,
            profile_data=ngo_profile_data(),
        )
        self.assertEqual(user.approval_status, ApprovalStatus.PENDING)

    def test_duplicate_email_raises_duplicate_email_error(self):
        from apps.accounts.services import DuplicateEmailError

        register_user(
            email="dup@example.com",
            password="strongpass123",
            full_name="First",
            role=Role.PATIENT,
            is_adult_confirmed=True,
            profile_data=dict(PATIENT_PROFILE_DATA),
        )
        with self.assertRaises(DuplicateEmailError):
            register_user(
                email="dup@example.com",
                password="strongpass123",
                full_name="Second",
                role=Role.PATIENT,
                is_adult_confirmed=True,
                profile_data=dict(PATIENT_PROFILE_DATA),
            )

    def test_unrelated_integrity_error_is_reraised_unmodified(self):
        from unittest.mock import patch

        from django.db import IntegrityError

        with patch(
            "apps.accounts.services.User.objects.create_user",
            side_effect=IntegrityError("some other constraint violation"),
        ):
            with self.assertRaises(IntegrityError):
                register_user(
                    email="neverexisted@example.com",
                    password="strongpass123",
                    full_name="Nobody",
                    role=Role.PATIENT,
                    is_adult_confirmed=True,
                    profile_data=dict(PATIENT_PROFILE_DATA),
                )

    def test_registration_lowercases_email(self):
        user = register_user(
            email="Bob@Example.COM",
            password="strongpass123",
            full_name="Bob",
            role=Role.PATIENT,
            is_adult_confirmed=True,
            profile_data=dict(PATIENT_PROFILE_DATA),
        )
        self.assertEqual(user.email, "bob@example.com")

    def test_registration_logs_audit_event(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            register_user(
                email="audited@example.com",
                password="strongpass123",
                full_name="Audited User",
                role=Role.PATIENT,
                is_adult_confirmed=True,
                profile_data=dict(PATIENT_PROFILE_DATA),
            )
        payload = __import__("json").loads(captured.records[0].getMessage())
        self.assertEqual(payload["event_type"], "register")
        self.assertEqual(payload["email"], "audited@example.com")


class AuthenticateAndCheckApprovalTests(TestCase):
    def setUp(self):
        self.password = "strongpass123"
        self.patient = User.objects.create_user(
            email="patient2@example.com",
            password=self.password,
            full_name="Pat Ient",
            role=Role.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.pending_psych = User.objects.create_user(
            email="pending@example.com",
            password=self.password,
            full_name="Pending Doc",
            role=Role.PSYCHOLOGIST,
            approval_status=ApprovalStatus.PENDING,
        )
        self.rejected_ngo = User.objects.create_user(
            email="rejected@example.com",
            password=self.password,
            full_name="Rejected NGO",
            role=Role.NGO,
            approval_status=ApprovalStatus.REJECTED,
        )

    def test_approved_user_authenticates(self):
        from apps.accounts.services import authenticate_and_check_approval

        user = authenticate_and_check_approval(
            email="patient2@example.com", password=self.password
        )
        self.assertEqual(user, self.patient)

    def test_registration_and_login_are_case_insensitive_for_email(self):
        from apps.accounts.services import authenticate_and_check_approval

        registered = register_user(
            email="Bob@Example.COM",
            password=self.password,
            full_name="Bob",
            role=Role.PATIENT,
            is_adult_confirmed=True,
            profile_data=dict(PATIENT_PROFILE_DATA),
        )
        self.assertEqual(registered.email, "bob@example.com")

        user = authenticate_and_check_approval(
            email="BOB@example.com", password=self.password
        )
        self.assertEqual(user, registered)

    def test_wrong_password_raises_invalid_credentials(self):
        from apps.accounts.services import (
            InvalidCredentialsError,
            authenticate_and_check_approval,
        )

        with self.assertRaises(InvalidCredentialsError):
            authenticate_and_check_approval(
                email="patient2@example.com", password="wrongpass"
            )

    def test_pending_account_raises_pending_approval(self):
        from apps.accounts.services import (
            AccountPendingApprovalError,
            authenticate_and_check_approval,
        )

        with self.assertRaises(AccountPendingApprovalError):
            authenticate_and_check_approval(
                email="pending@example.com", password=self.password
            )

    def test_rejected_account_raises_rejected(self):
        from apps.accounts.services import (
            AccountRejectedError,
            authenticate_and_check_approval,
        )

        with self.assertRaises(AccountRejectedError):
            authenticate_and_check_approval(
                email="rejected@example.com", password=self.password
            )

    def test_successful_login_logs_audit_event(self):
        from apps.accounts.services import authenticate_and_check_approval

        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            authenticate_and_check_approval(
                email="patient2@example.com", password=self.password
            )
        payload = __import__("json").loads(captured.records[0].getMessage())
        self.assertEqual(payload["event_type"], "login")

    def test_failed_login_logs_audit_event(self):
        from apps.accounts.services import (
            InvalidCredentialsError,
            authenticate_and_check_approval,
        )

        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            with self.assertRaises(InvalidCredentialsError):
                authenticate_and_check_approval(
                    email="patient2@example.com", password="wrongpass"
                )
        payload = __import__("json").loads(captured.records[0].getMessage())
        self.assertEqual(payload["event_type"], "login_failed")
        self.assertFalse(payload["success"])


class AuditHelperSmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="smoke@example.com",
            password="strongpass123",
            full_name="Smoke User",
            role=Role.PATIENT,
        )

    def test_record_token_refresh_emits_audit_event(self):
        from apps.accounts.services import record_token_refresh

        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            record_token_refresh(user=self.user, ip="127.0.0.1")
        payload = __import__("json").loads(captured.records[0].getMessage())
        self.assertEqual(payload["event_type"], "token_refresh")
        self.assertEqual(payload["user_id"], self.user.id)

    def test_record_logout_emits_audit_event(self):
        from apps.accounts.services import record_logout

        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            record_logout(user=self.user, ip="127.0.0.1")
        payload = __import__("json").loads(captured.records[0].getMessage())
        self.assertEqual(payload["event_type"], "logout")
        self.assertEqual(payload["user_id"], self.user.id)


class RegisterUserProfileOrchestrationTests(TestCase):
    def test_each_role_gets_its_profile_and_adult_timestamp(self):
        patient = register_user(
            email="p@example.com",
            password="strongpass123",
            full_name="P Test",
            role=Role.PATIENT,
            is_adult_confirmed=True,
            profile_data=dict(PATIENT_PROFILE_DATA),
        )
        psych = register_user(
            email="d@example.com",
            password="strongpass123",
            full_name="D Test",
            role=Role.PSYCHOLOGIST,
            is_adult_confirmed=True,
            profile_data=psychologist_profile_data(),
        )
        ngo = register_user(
            email="n@example.com",
            password="strongpass123",
            full_name="N Test",
            role=Role.NGO,
            is_adult_confirmed=True,
            profile_data=ngo_profile_data(),
        )
        self.assertTrue(hasattr(patient, "patient_profile"))
        self.assertTrue(hasattr(psych, "psychologist_profile"))
        self.assertTrue(hasattr(ngo, "ngo_profile"))
        for user in (patient, psych, ngo):
            self.assertIsNotNone(user.adult_confirmed_at)

    def test_missing_adult_declaration_rejected_and_nothing_created(self):
        from core.exceptions import DomainValidationError

        with self.assertRaises(DomainValidationError):
            register_user(
                email="kid@example.com",
                password="strongpass123",
                full_name="K Test",
                role=Role.PATIENT,
                is_adult_confirmed=False,
                profile_data=dict(PATIENT_PROFILE_DATA),
            )
        self.assertFalse(User.objects.filter(email="kid@example.com").exists())

    def test_profile_failure_rolls_back_user(self):
        from unittest.mock import patch

        with patch.dict(
            "apps.accounts.services.PROFILE_CREATORS",
            {Role.PATIENT: lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))},
        ):
            with self.assertRaises(RuntimeError):
                register_user(
                    email="rollback@example.com",
                    password="strongpass123",
                    full_name="R Test",
                    role=Role.PATIENT,
                    is_adult_confirmed=True,
                    profile_data=dict(PATIENT_PROFILE_DATA),
                )
        self.assertFalse(User.objects.filter(email="rollback@example.com").exists())

    def test_duplicate_license_rolls_back_second_user(self):
        from apps.psychologists.services import DuplicateLicenseError

        register_user(
            email="d1@example.com",
            password="strongpass123",
            full_name="Dee One",
            role=Role.PSYCHOLOGIST,
            is_adult_confirmed=True,
            profile_data=psychologist_profile_data(),
        )
        with self.assertRaises(DuplicateLicenseError):
            register_user(
                email="d2@example.com",
                password="strongpass123",
                full_name="Dee Two",
                role=Role.PSYCHOLOGIST,
                is_adult_confirmed=True,
                profile_data=psychologist_profile_data(),
            )
        self.assertFalse(User.objects.filter(email="d2@example.com").exists())

    def test_no_audit_event_when_registration_fails(self):
        from core.exceptions import DomainValidationError

        with self.assertNoLogs("mindcare.audit", level="INFO"):
            with self.assertRaises(DomainValidationError):
                register_user(
                    email="x@example.com",
                    password="strongpass123",
                    full_name="X Test",
                    role=Role.PATIENT,
                    is_adult_confirmed=True,
                    profile_data={"timezone": "Nope/Nope"},
                )
