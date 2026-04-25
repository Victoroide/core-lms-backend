from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin


class Course(SoftDeleteMixin, models.Model):
    """Academic course definition within the LMS platform.

    Attributes:
        name (str): Human-readable course name.
        code (str): Unique short code identifying the course.
        description (str): Free-text course description.
        created_at (datetime): Timestamp set when the course is created.
    """

    semester = models.ForeignKey(
        "Semester",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "course"
        ordering = ["code"]

    def __str__(self):
        """Return ``"<code> -- <name>"`` for admin and shell display.

        Returns:
            str: Human-readable course label.
        """
        return f"{self.code} -- {self.name}"
