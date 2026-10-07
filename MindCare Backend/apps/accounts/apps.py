from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        # Registers the drf-spectacular OpenAPI extension for our JWT auth class.
        from apps.accounts import schema  # noqa: F401
