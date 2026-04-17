from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin


class Career(SoftDeleteMixin, models.Model):
    """A university degree program (e.g. Ingeniería en Sistemas).

    Serves as the top-level node of the academic ontology hierarchy:
    Career → Semester → Course → Module → Lesson.

    Attributes:
        name (str): Human-readable name of the degree program.
        code (str): Unique short identifier (e.g. SIS, MED).
        description (str): Extended description of the program scope.
        created_at (datetime): Timestamp of record creation.
    """

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "career"
        ordering = ["code"]

    def __str__(self):
        """Return a display string combining code and name.

        Returns:
            str: Formatted career identifier.
        """
        return f"{self.code} -- {self.name}"
