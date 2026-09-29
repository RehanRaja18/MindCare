"""Django admin for NGO profiles. Credential fields ARE editable here: the
interim correction path until Phase 2.5's re-review flow."""

from django import forms
from django.contrib import admin

from apps.ngo.models import NGOProfile, NGOServiceArea
from core.validators import (
    normalize_display_text,
    normalize_email_address,
    normalize_identifier,
)


class NGOProfileAdminForm(forms.ModelForm):
    """Same normalization as the service layer, so a value corrected here still
    matches what the API's locked-credential comparison expects."""

    class Meta:
        model = NGOProfile
        fields = "__all__"

    def clean_registration_number(self):
        return normalize_identifier(self.cleaned_data["registration_number"])

    def clean_organization_name(self):
        return normalize_display_text(self.cleaned_data["organization_name"])

    def clean_registering_authority(self):
        return normalize_display_text(self.cleaned_data["registering_authority"])

    def clean_official_email(self):
        return normalize_email_address(self.cleaned_data["official_email"])


class NGOServiceAreaInline(admin.TabularInline):
    model = NGOServiceArea
    extra = 0
    autocomplete_fields = ["country", "city"]


@admin.register(NGOProfile)
class NGOProfileAdmin(admin.ModelAdmin):
    form = NGOProfileAdminForm
    list_display = [
        "organization_name",
        "registration_number",
        "registration_country",
        "country",
    ]
    list_filter = ["registration_country", "country"]
    search_fields = ["organization_name", "registration_number", "user__email"]
    autocomplete_fields = ["registration_country", "country", "city"]
    readonly_fields = ["user", "created_at", "updated_at"]

    def has_add_permission(self, request):
        # Profiles are created only by register_user(), never in admin.
        return False

    inlines = [NGOServiceAreaInline]
