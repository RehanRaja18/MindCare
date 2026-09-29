"""Django admin smoke tests for accounts."""

from django.contrib.admin.sites import site
from django.test import TestCase

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
