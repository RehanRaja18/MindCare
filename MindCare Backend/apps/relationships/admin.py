"""Read-only Django admin for care relationships (support visibility only).

Patients are shown by pseudonym. Rows can't be added, changed or deleted here.
PROTECT on the profile foreign keys means a user with relationship rows can't be
deleted from the User admin; delete the rows first (SQL in docs/deployment.md).
"""

from django.contrib import admin

from apps.relationships.models import CareRelationship


@admin.register(CareRelationship)
class CareRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "patient_pseudonym",
        "psychologist",
        "status",
        "requested_at",
        "responded_at",
        "ended_at",
        "ended_by",
        "end_reason",
        "decline_reason",
    ]
    list_filter = ["status", "end_reason", "ended_by"]
    fields = [
        "status",
        "requested_at",
        "expires_at",
        "responded_at",
        "decline_reason",
        "cooldown_until",
        "ended_at",
        "ended_by",
        "end_reason",
    ]

    @admin.display(description="Patient")
    def patient_pseudonym(self, obj):
        return obj.patient.pseudonym

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("patient", "psychologist")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
