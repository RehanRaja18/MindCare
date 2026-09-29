"""Django admin for users — the interim approval path for pending psychologist
and NGO accounts until Phase 2.5's approval endpoints.

Deliberately NOT editable here:
- password (use the manage.py changepassword command)
- is_superuser and is_super_admin (Phase 2.5 owns promote/demote and the
  at-least-one-super-admin invariant)
- role (read-only; changing it would leave a profile that doesn't match the role;
  users are created only through accounts.services.register_user(), which creates
  the role's profile in the same transaction)

Users cannot be added through this interface; users are created only through
accounts.services.register_user(). Admin accounts come from manage.py createsuperuser.
"""

from django.contrib import admin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "full_name",
        "role",
        "approval_status",
        "is_active",
        "created_at",
    ]
    list_filter = ["role", "approval_status", "is_active"]
    search_fields = ["email", "full_name"]
    ordering = ["-created_at"]
    fields = [
        "email",
        "full_name",
        "role",
        "approval_status",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_super_admin",
        "adult_confirmed_at",
        "last_login",
        "created_at",
        "updated_at",
    ]
    readonly_fields = [
        "role",
        "is_superuser",
        "is_super_admin",
        "adult_confirmed_at",
        "last_login",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        # Users are created only through accounts.services.register_user(), which
        # creates the role's profile in the same transaction ("every user has a
        # profile"). Admin accounts come from `manage.py createsuperuser`.
        return False
