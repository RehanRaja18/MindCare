"""Django admin for reference data — the place admins correct it."""

from django.contrib import admin

from apps.reference.models import City, Country, Language, Specialization


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "is_verified"]
    list_filter = ["is_verified", "country"]
    list_editable = ["is_verified"]
    search_fields = ["name"]
    autocomplete_fields = ["country"]
    actions = ["mark_verified"]

    @admin.action(description="Mark selected cities as verified")
    def mark_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"{updated} city(ies) marked as verified.")


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["slug", "name"]
    prepopulated_fields = {"slug": ["name"]}
