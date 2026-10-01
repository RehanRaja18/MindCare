"""Django admin tests for patient profiles."""

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase

from apps.accounts.models import Role, User
from apps.patients.models import PatientProfile
from apps.patients.services import create_patient_profile
from core.testing import PATIENT_PROFILE_DATA, admin_change_form_data, make_user


class PatientProfileAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.client.force_login(self.root)
        self.user = make_user(role=Role.PATIENT)
        self.profile = create_patient_profile(user=self.user, **PATIENT_PROFILE_DATA)

    def test_add_is_disabled(self):
        self.assertEqual(
            self.client.get("/admin/patients/patientprofile/add/").status_code, 403
        )

    def test_user_is_read_only_on_change(self):
        request = RequestFactory().get("/")
        request.user = self.root
        model_admin = site._registry[PatientProfile]
        self.assertIn("user", model_admin.get_readonly_fields(request, self.profile))

    def test_posting_a_different_user_does_not_reassign(self):
        other = make_user(role=Role.PATIENT)
        url = f"/admin/patients/patientprofile/{self.profile.pk}/change/"
        data = admin_change_form_data(self.client.get(url))
        data["user"] = str(other.pk)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.user_id, self.user.pk)
