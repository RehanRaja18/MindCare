"""Database models for the accounts app: the custom User model and roles."""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from core.fields import PersonNameField
from core.models import ValidatedModelMixin


class Role(models.TextChoices):
    PATIENT = "patient", "Patient"
    PSYCHOLOGIST = "psychologist", "Psychologist"
    ADMIN = "admin", "Admin"
    NGO = "ngo", "NGO"


class ApprovalStatus(models.TextChoices):
    APPROVED = "approved", "Approved"
    PENDING = "pending", "Pending"
    REJECTED = "rejected", "Rejected"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, *, full_name, role, **extra_fields):
        return self._create_user(
            email, password, full_name=full_name, role=role, **extra_fields
        )

    def create_superuser(
        self, email, password=None, *, full_name="Super Admin", **extra_fields
    ):
        # Superusers are always admins, regardless of what a caller passes in —
        # this is the system's bootstrap mechanism for its first super-admin.
        extra_fields["role"] = Role.ADMIN
        extra_fields["approval_status"] = ApprovalStatus.APPROVED
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["is_super_admin"] = True
        return self._create_user(email, password, full_name=full_name, **extra_fields)


class User(ValidatedModelMixin, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    # Column stays 255; the name rule caps new values at 100 (validation-rules.md).
    full_name = PersonNameField(max_length=255, label="Full name")
    role = models.CharField(max_length=20, choices=Role.choices)
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.APPROVED
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_super_admin = models.BooleanField(default=False)
    # Set when the user declared "I am 18 or older" at public registration
    # (docs/decisions.md, 2026-09-26). NULL for createsuperuser accounts.
    adult_confirmed_at = models.DateTimeField(null=True, blank=True)
    # Written only for psychologists (Phase 3 activity tracking, at most every
    # 15 minutes); shown to patients only as a band, never as a timestamp.
    last_active_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    def __str__(self):
        return self.email
