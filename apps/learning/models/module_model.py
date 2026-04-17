from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin


class Module(SoftDeleteMixin, models.Model):
    """A thematic section within a Course.

    Modules subdivide a course into logical content blocks
    (e.g. "Module 1: Introduction to OOP").

    Attributes:
        course (Course): The parent course.
        title (str): Module title.
        description (str): Extended description of the module scope.
        order (int): Display order within the course.
    """

    course = models.ForeignKey(
        "learning.Course",
        on_delete=models.CASCADE,
        related_name="modules",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "module"
        ordering = ["course", "order"]

    def __str__(self):
        """Return a display string for the module.

        Returns:
            str: Formatted module identifier.
        """
        return f"M{self.order}: {self.title} ({self.course.code})"
