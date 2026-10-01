"""Django admin tests for psychologist profiles."""

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase

from apps.accounts.models import Role, User
from apps.psychologists.models import PsychologistProfile
from apps.psychologists.services import create_psychologist_profile
from rest_framework.test import APIClient

from core.testing import (
    admin_change_form_data,
    make_user,
    psychologist_profile_data,
    psychologist_profile_payload,
)


class PsychologistProfileAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.client.force_login(self.root)
        self.user = make_user(role=Role.PSYCHOLOGIST)
        self.profile = create_psychologist_profile(
            user=self.user, **psychologist_profile_data()
        )
        self.url = f"/admin/psychologists/psychologistprofile/{self.profile.pk}/change/"

    def test_add_is_disabled(self):
        response = self.client.get("/admin/psychologists/psychologistprofile/add/")
        self.assertEqual(response.status_code, 403)

    def test_user_is_read_only_on_change(self):
        request = RequestFactory().get("/")
        request.user = self.root
        model_admin = site._registry[PsychologistProfile]
        self.assertIn("user", model_admin.get_readonly_fields(request, self.profile))

    def test_posting_a_different_user_does_not_reassign(self):
        other = make_user(role=Role.PSYCHOLOGIST)
        data = admin_change_form_data(self.client.get(self.url))
        data["user"] = str(other.pk)
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.user_id, self.user.pk)

    def test_credential_edits_are_normalized(self):
        data = admin_change_form_data(self.client.get(self.url))
        data["license_number"] = "pmdc-12345 "
        data["license_issuing_authority"] = "  Pakistan   Medical  Commission "
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.license_number, "PMDC-12345")
        self.assertEqual(
            self.profile.license_issuing_authority, "Pakistan Medical Commission"
        )
        # A full-object PATCH echoing the stored credentials is not "changed".
        api = APIClient()
        api.force_authenticate(self.user)
        r = api.patch(
            "/api/v1/psychologists/me/",
            psychologist_profile_payload(
                license_number=self.profile.license_number,
                license_issuing_authority=self.profile.license_issuing_authority,
            ),
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
