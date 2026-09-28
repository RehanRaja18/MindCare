"""Django admin for patient profiles.

Known limitation (spec §5.3): viewing a patient here shows the real name without
an identity_reveal log. Phase 2.5's admin API must use the logged selector.
"""

from django.contrib import admin

from apps.patients.models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ["pseudonym", "is_profile_public", "country", "created_at"]
    list_filter = ["is_profile_public", "country"]
    search_fields = ["pseudonym", "user__email"]
    readonly_fields = ["pseudonym", "created_at", "updated_at"]
    autocomplete_fields = ["country", "city", "preferred_language"]
    raw_id_fields = ["user"]
