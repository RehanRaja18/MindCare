"""Tests for the shared RBAC permission classes in core/permissions.py.

These live in apps/accounts/tests/ (rather than a tests/ dir under core/,
since core/ is not a Django app) because apps/accounts owns the User model
these permission classes are exercised against.
"""

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.accounts.models import ApprovalStatus, Role, User
from core.permissions import IsAdmin, IsNGO, IsOwnerOfObject, IsPatient, IsPsychologist


class RolePermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.patient = User.objects.create_user(
            email="rp_patient@example.com",
            password="x",
            full_name="P Test",
            role=Role.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.psychologist = User.objects.create_user(
            email="rp_psych@example.com",
            password="x",
            full_name="D Test",
            role=Role.PSYCHOLOGIST,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.admin = User.objects.create_user(
            email="rp_admin@example.com",
            password="x",
            full_name="A Test",
            role=Role.ADMIN,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.ngo = User.objects.create_user(
            email="rp_ngo@example.com",
            password="x",
            full_name="N Test",
            role=Role.NGO,
            approval_status=ApprovalStatus.APPROVED,
        )

    def _request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_is_patient(self):
        self.assertTrue(
            IsPatient().has_permission(self._request_for(self.patient), None)
        )
        self.assertFalse(
            IsPatient().has_permission(self._request_for(self.psychologist), None)
        )

    def test_is_psychologist(self):
        self.assertTrue(
            IsPsychologist().has_permission(self._request_for(self.psychologist), None)
        )
        self.assertFalse(
            IsPsychologist().has_permission(self._request_for(self.patient), None)
        )

    def test_is_admin(self):
        self.assertTrue(IsAdmin().has_permission(self._request_for(self.admin), None))
        self.assertFalse(IsAdmin().has_permission(self._request_for(self.ngo), None))

    def test_is_ngo(self):
        self.assertTrue(IsNGO().has_permission(self._request_for(self.ngo), None))
        self.assertFalse(IsNGO().has_permission(self._request_for(self.admin), None))


class DummyOwnedObject:
    """A stand-in for a real model (e.g. a future Patient record) with an owner."""

    def __init__(self, owner):
        self.owner = owner


class IsOwnerOfDummyObject(IsOwnerOfObject):
    def get_owner_user(self, obj):
        return obj.owner


class IsOwnerOfObjectTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="x",
            full_name="Owner",
            role=Role.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.stranger = User.objects.create_user(
            email="stranger@example.com",
            password="x",
            full_name="Stranger",
            role=Role.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.obj = DummyOwnedObject(owner=self.owner)

    def test_owner_has_object_permission(self):
        request = self.factory.get("/")
        request.user = self.owner
        self.assertTrue(
            IsOwnerOfDummyObject().has_object_permission(request, None, self.obj)
        )

    def test_non_owner_denied_object_permission(self):
        request = self.factory.get("/")
        request.user = self.stranger
        self.assertFalse(
            IsOwnerOfDummyObject().has_object_permission(request, None, self.obj)
        )

    def test_base_class_raises_not_implemented_without_subclassing(self):
        request = self.factory.get("/")
        request.user = self.owner
        with self.assertRaises(NotImplementedError):
            IsOwnerOfObject().has_object_permission(request, None, self.obj)
