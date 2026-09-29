"""Django admin tests for NGO profiles."""

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase

from apps.accounts.models import Role, User
from apps.ngo.models import NGOProfile
from apps.ngo.services import create_ngo_profile
from core.testing import admin_change_form_data, make_user, ngo_profile_data


class NGOProfileAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.client.force_login(self.root)
        self.user = make_user(role=Role.NGO)
        self.profile = create_ngo_profile(user=self.user, **ngo_profile_data())
        self.url = f"/admin/ngo/ngoprofile/{self.profile.pk}/change/"

    def test_add_is_disabled(self):
        self.assertEqual(self.client.get("/admin/ngo/ngoprofile/add/").status_code, 403)

    def test_user_is_read_only_on_change(self):
        request = RequestFactory().get("/")
        request.user = self.root
        model_admin = site._registry[NGOProfile]
        self.assertIn("user", model_admin.get_readonly_fields(request, self.profile))

    def test_posting_a_different_user_does_not_reassign(self):
        other = make_user(role=Role.NGO)
        data = admin_change_form_data(self.client.get(self.url))
        data["user"] = str(other.pk)
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.user_id, self.user.pk)
