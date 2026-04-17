from django.apps import AppConfig


class LearningConfig(AppConfig):
    """Django application configuration for the learning module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.learning"
    label = "learning"
    verbose_name = "Learning Management"
