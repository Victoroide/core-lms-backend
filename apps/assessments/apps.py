from django.apps import AppConfig


class AssessmentsConfig(AppConfig):
    """Django application configuration for the assessments module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assessments"
    label = "assessments"
    verbose_name = "Assessments & Proctoring"
