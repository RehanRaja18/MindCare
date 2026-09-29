"""Django admin for users — the interim approval path for pending psychologist
and NGO accounts until Phase 2.5's approval endpoints.

Deliberately NOT editable here: password (use the manage.py changepassword
command), is_superuser and is_super_admin (Phase 2.5 owns promote/demote and
the at-least-one-super-admin invariant).
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
        "is_superuser",
        "is_super_admin",
        "adult_confirmed_at",
        "last_login",
        "created_at",
        "updated_at",
    ]
