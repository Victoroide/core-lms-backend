from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin


class Lesson(SoftDeleteMixin, models.Model):
    """An individual teaching unit within a Module.

    Lessons are the atomic pedagogical unit where resources are
    attached and assignments are defined.

    Attributes:
        module (Module): The parent module.
        title (str): Lesson title.
        content (str): Rich-text or markdown lesson body.
        order (int): Display order within the module.
    """

    module = models.ForeignKey(
        "learning.Module",
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "lesson"
        ordering = ["module", "order"]

    def __str__(self):
        """Return a display string for the lesson.

        Returns:
            str: Formatted lesson identifier.
        """
        return f"L{self.order}: {self.title}"
