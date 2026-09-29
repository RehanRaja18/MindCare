"""Django admin for NGO profiles. Credential fields ARE editable here: the
interim correction path until Phase 2.5's re-review flow."""

from django.contrib import admin

from apps.ngo.models import NGOProfile, NGOServiceArea


class NGOServiceAreaInline(admin.TabularInline):
    model = NGOServiceArea
    extra = 0
    autocomplete_fields = ["country", "city"]


@admin.register(NGOProfile)
class NGOProfileAdmin(admin.ModelAdmin):
    list_display = [
        "organization_name",
        "registration_number",
        "registration_country",
        "country",
    ]
    list_filter = ["registration_country", "country"]
    search_fields = ["organization_name", "registration_number", "user__email"]
    autocomplete_fields = ["registration_country", "country", "city"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [NGOServiceAreaInline]
