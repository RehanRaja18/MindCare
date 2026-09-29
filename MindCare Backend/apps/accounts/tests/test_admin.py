"""Django admin smoke tests for accounts."""

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase

from apps.accounts.models import ApprovalStatus, Role, User
from core.testing import make_user


class UserAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.client.force_login(self.root)

    def test_user_registered_with_safe_readonly_fields(self):
        model_admin = site._registry[User]
        readonly = set(model_admin.get_readonly_fields(None))
        self.assertTrue(
            {"is_superuser", "is_super_admin", "adult_confirmed_at"} <= readonly
        )
        self.assertNotIn("password", model_admin.get_fields(None))

    def test_admin_can_approve_pending_psychologist(self):
        pending = make_user(
            role=Role.PSYCHOLOGIST, approval_status=ApprovalStatus.PENDING
        )
        url = f"/admin/accounts/user/{pending.pk}/change/"
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(
            url,
            {
                "email": pending.email,
                "full_name": pending.full_name,
                "role": pending.role,
                "approval_status": ApprovalStatus.APPROVED,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, ApprovalStatus.APPROVED)

    def test_add_user_is_disabled(self):
        """Users can only be created through register_user(), not admin."""
        model_admin = site._registry[User]
        factory = RequestFactory()
        request = factory.get("/admin/accounts/user/add/")
        request.user = self.root
        self.assertFalse(model_admin.has_add_permission(request))
        response = self.client.get("/admin/accounts/user/add/")
        self.assertEqual(response.status_code, 403)

    def test_role_is_read_only_on_change(self):
        """Role is read-only when editing; changing it in the form is ignored."""
        patient = make_user(role=Role.PATIENT)
        model_admin = site._registry[User]
        factory = RequestFactory()
        request = factory.get(f"/admin/accounts/user/{patient.pk}/change/")
        request.user = self.root
        readonly = model_admin.get_readonly_fields(request, patient)
        self.assertIn("role", readonly)

        url = f"/admin/accounts/user/{patient.pk}/change/"
        response = self.client.post(
            url,
            {
                "email": patient.email,
                "full_name": patient.full_name,
                "role": Role.ADMIN,  # Try to change role
                "approval_status": patient.approval_status,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        patient.refresh_from_db()
        self.assertEqual(patient.role, Role.PATIENT)

    def test_superuser_flags_cannot_be_set_through_change_form(self):
        """is_super_admin and is_superuser are read-only and cannot be set through the form."""
        user = make_user(role=Role.ADMIN)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_super_admin)

        url = f"/admin/accounts/user/{user.pk}/change/"
        response = self.client.post(
            url,
            {
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "approval_status": user.approval_status,
                "is_active": "on",
                "is_superuser": "on",
                "is_super_admin": "on",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_super_admin)
