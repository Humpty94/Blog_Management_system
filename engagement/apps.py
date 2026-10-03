from django.apps import AppConfig


class EngagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "engagement"

    def ready(self) -> None:
        import engagement.signals  # noqa: F401
