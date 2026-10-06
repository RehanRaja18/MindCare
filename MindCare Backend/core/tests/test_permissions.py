"""Unit tests for the shared permission classes."""

from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.accounts.models import ApprovalStatus, Role
from core.permissions import IsApprovedPsychologist
from core.testing import make_admin, make_user


def _allowed(user):
    return IsApprovedPsychologist().has_permission(SimpleNamespace(user=user), None)


class IsApprovedPsychologistTests(TestCase):
    def test_approved_active_psychologist_allowed(self):
        self.assertTrue(_allowed(make_user(role=Role.PSYCHOLOGIST)))

    def test_pending_or_rejected_psychologist_denied(self):
        for approval in (ApprovalStatus.PENDING, ApprovalStatus.REJECTED):
            with self.subTest(approval=approval):
                user = make_user(role=Role.PSYCHOLOGIST, approval_status=approval)
                self.assertFalse(_allowed(user))

    def test_inactive_psychologist_denied(self):
        self.assertFalse(_allowed(make_user(role=Role.PSYCHOLOGIST, is_active=False)))

    def test_other_roles_and_anonymous_denied(self):
        self.assertFalse(_allowed(make_user(role=Role.PATIENT)))
        self.assertFalse(_allowed(make_user(role=Role.NGO)))
        self.assertFalse(_allowed(make_admin()))
        self.assertFalse(_allowed(AnonymousUser()))
        self.assertFalse(_allowed(None))
