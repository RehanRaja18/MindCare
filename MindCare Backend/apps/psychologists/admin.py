"""Django admin for psychologist profiles. Credential fields ARE editable here:
this is the interim correction path until Phase 2.5's re-review flow."""

from django.contrib import admin

from apps.psychologists.models import PsychologistProfile


@admin.register(PsychologistProfile)
class PsychologistProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "license_number",
        "license_issuing_country",
        "country",
        "created_at",
    ]
    list_filter = ["license_issuing_country", "country"]
    search_fields = ["user__email", "user__full_name", "license_number"]
    autocomplete_fields = ["license_issuing_country", "country", "city"]
    filter_horizontal = ["specializations", "languages"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]
