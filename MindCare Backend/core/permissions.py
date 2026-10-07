"""
Shared, app-agnostic DRF permission classes.

Role-level checks (IsPatient, IsPsychologist, IsAdmin, IsNGO) live here since
more than one app needs them. Object-level ownership checks specific to a
single app's data (e.g. "is this psychologist's own patient") belong in that
app's own permissions.py, built on IsOwnerOfObject below — per the project's
hard rule that role-based access alone is never sufficient.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import ApprovalStatus, Role


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.PATIENT
        )


class IsPsychologist(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.PSYCHOLOGIST
        )


class IsApprovedPsychologist(BasePermission):
    """A psychologist whose account is active and approved. Pending (paused for
    re-review), rejected and deactivated psychologists are refused. Used with
    IsPsychologist on endpoints that act on patients; the Phase 2 /me/ profile
    endpoints deliberately don't use it, since a pending psychologist needs them."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == Role.PSYCHOLOGIST
            and user.is_active
            and user.approval_status == ApprovalStatus.APPROVED
        )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsNGO(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.NGO
        )


class IsOwnerOfObject(BasePermission):
    """
    Subclass and implement get_owner_user() to compare the requesting user
    against the resource's actual owner, e.g.:

        class IsAssignedPsychologist(IsOwnerOfObject):
            def get_owner_user(self, obj):
                return obj.assigned_psychologist.user
    """

    def get_owner_user(self, obj):
        raise NotImplementedError(
            "Subclasses of IsOwnerOfObject must implement get_owner_user()."
        )

    def has_object_permission(self, request, view, obj):
        return self.get_owner_user(obj) == request.user
