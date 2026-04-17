from django.apps import AppConfig


class CurriculumConfig(AppConfig):
    """Django application configuration for the curriculum module.

    Owns file-based pedagogy entities: Assignment and Submission.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.curriculum"
    label = "curriculum"
