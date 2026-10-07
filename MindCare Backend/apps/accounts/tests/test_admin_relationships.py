"""Deactivating or rejecting a user in Django admin ends their relationships."""

import json

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

    def _post(self, user=None, **changes):
        url = f"/admin/accounts/user/{(user or self.psych.user).pk}/change/"
        data = admin_change_form_data(self.client.get(url))
        data.update(changes)
        if changes.get("is_active") is False:
            data.pop("is_active", None)
        return self.client.post(url, data)

    def _assert_ended_by_system(self):
        self.rel.refresh_from_db()
        self.assertEqual(
            (self.rel.status, self.rel.ended_by, self.rel.end_reason),
            (RelationshipStatus.ENDED, "system", "account_unavailable"),
        )

    def test_deactivating_ends_relationship(self):
        self.assertEqual(self._post(is_active=False).status_code, 302)
        self._assert_ended_by_system()

    def test_rejecting_ends_relationship(self):
        self.assertEqual(
            self._post(approval_status=ApprovalStatus.REJECTED).status_code, 302
        )
        self._assert_ended_by_system()

    def test_deactivating_patient_expires_their_pending_request(self):
        other_patient = make_patient()
        pending = services.request_psychologist(
            patient_user=other_patient.user, psychologist_id=make_psychologist().pk
        )
        self.assertEqual(
            self._post(user=other_patient.user, is_active=False).status_code, 302
        )
        pending.refresh_from_db()
        self.assertEqual(pending.status, RelationshipStatus.EXPIRED)

    def test_ended_audit_line_written_after_admin_request_commits(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            with self.captureOnCommitCallbacks(execute=True):
                response = self._post(is_active=False)
        self.assertEqual(response.status_code, 302)
        payloads = [json.loads(r.getMessage()) for r in captured.records]
        self.assertIn(
            ("ended", "system", self.rel.pk),
            [
                (p.get("event"), p.get("actor_role"), p.get("relationship_id"))
                for p in payloads
            ],
        )

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
