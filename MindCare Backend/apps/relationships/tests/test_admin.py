"""Django admin for CareRelationship is read-only and shows pseudonyms."""

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.relationships.models import REQUEST_EXPIRY, CareRelationship
from core.testing import make_patient, make_psychologist


class CareRelationshipAdminTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.client.force_login(self.root)
        now = timezone.now()
        self.patient = make_patient(full_name="Ayesha Khan")
        self.rel = CareRelationship.objects.create(
            patient=self.patient,
            psychologist=make_psychologist(),
            requested_at=now,
            expires_at=now + REQUEST_EXPIRY,
        )

    def test_no_add_change_or_delete(self):
        admin = site._registry[CareRelationship]
        request = RequestFactory().get("/")
        request.user = self.root
        self.assertFalse(admin.has_add_permission(request))
        self.assertFalse(admin.has_change_permission(request, self.rel))
        self.assertFalse(admin.has_delete_permission(request, self.rel))

    def test_changelist_shows_pseudonym_not_name(self):
        response = self.client.get("/admin/relationships/carerelationship/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.pseudonym)
        self.assertNotContains(response, "Ayesha Khan")
