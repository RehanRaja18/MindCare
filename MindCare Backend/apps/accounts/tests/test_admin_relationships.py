"""Deactivating or rejecting a user in Django admin ends their relationships."""

from django.test import TestCase

from apps.accounts.models import ApprovalStatus, User
from apps.relationships import services
from apps.relationships.models import RelationshipStatus
from core.testing import admin_change_form_data, make_patient, make_psychologist


class UserAdminEndsRelationshipsTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.client.force_login(self.root)
        self.patient = make_patient()
        self.psych = make_psychologist()
        rel = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )
        self.rel = services.accept_request(
            psychologist_user=self.psych.user, relationship_id=rel.pk
        )
        self.url = f"/admin/accounts/user/{self.psych.user.pk}/change/"

    def _post(self, **changes):
        data = admin_change_form_data(self.client.get(self.url))
        data.update(changes)
        if changes.get("is_active") is False:
            data.pop("is_active", None)
        return self.client.post(self.url, data)

    def test_deactivating_ends_relationship(self):
        self.assertEqual(self._post(is_active=False).status_code, 302)
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ENDED)

    def test_rejecting_ends_relationship(self):
        self.assertEqual(
            self._post(approval_status=ApprovalStatus.REJECTED).status_code, 302
        )
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ENDED)

    def test_moving_to_pending_only_pauses(self):
        self.assertEqual(
            self._post(approval_status=ApprovalStatus.PENDING).status_code, 302
        )
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)

    def test_unrelated_edit_ends_nothing(self):
        self.assertEqual(self._post(full_name="New Name").status_code, 302)
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
