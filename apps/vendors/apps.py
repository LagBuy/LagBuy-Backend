from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vendors"

    def ready(self):
        # import signals to register them
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
