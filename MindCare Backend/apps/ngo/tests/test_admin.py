"""Django admin tests for NGO profiles."""

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase

from apps.accounts.models import Role, User
from apps.ngo.models import NGOProfile
from apps.ngo.services import create_ngo_profile
from rest_framework.test import APIClient

from core.testing import (
    admin_change_form_data,
    make_user,
    ngo_profile_data,
    ngo_profile_payload,
)


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

    def test_credential_and_email_edits_are_normalized(self):
        data = admin_change_form_data(self.client.get(self.url))
        data["registration_number"] = "secp-0001 "
        data["organization_name"] = "  Helping   Hands "
        data["registering_authority"] = " SECP  "
        data["official_email"] = "  Info@Example.ORG "
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.registration_number, "SECP-0001")
        self.assertEqual(self.profile.organization_name, "Helping Hands")
        self.assertEqual(self.profile.registering_authority, "SECP")
        self.assertEqual(self.profile.official_email, "info@example.org")
        api = APIClient()
        api.force_authenticate(self.user)
        r = api.patch(
            "/api/v1/ngo/me/",
            ngo_profile_payload(
                registration_number=self.profile.registration_number,
                organization_name=self.profile.organization_name,
                registering_authority=self.profile.registering_authority,
                official_email=self.profile.official_email,
            ),
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
