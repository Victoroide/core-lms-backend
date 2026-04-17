from django.conf import settings
from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin


class Assignment(SoftDeleteMixin, models.Model):
    """A tutor-created assignment attached to a specific Lesson.

    Provides the file-based pedagogy mechanism where tutors define
    deliverables and students upload submissions.

    Attributes:
        lesson (Lesson): The parent lesson (owned by learning app).
        created_by (LMSUser): The tutor who created this assignment.
        title (str): Assignment title.
        description (str): Detailed instructions for the assignment.
        due_date (datetime): Submission deadline.
        max_score (Decimal): Maximum achievable score.
        created_at (datetime): Timestamp of creation.
    """

    lesson = models.ForeignKey(
        "learning.Lesson",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_assignments",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    due_date = models.DateTimeField(null=True, blank=True)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "assignment"
        verbose_name = "Lesson Assignment"
        verbose_name_plural = "Lesson Assignments"
        ordering = ["-created_at"]

    def __str__(self):
        """Return a display string for the assignment.

        Returns:
            str: Assignment title and parent lesson.
        """
        return f"{self.title} (Lesson: {self.lesson.title})"
