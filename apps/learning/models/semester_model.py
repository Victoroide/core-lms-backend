from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin


class Semester(SoftDeleteMixin, models.Model):
    """An academic period within a Career (degree program).

    Each semester groups a set of courses offered during a specific
    year and period (I, II, or Summer).

    Attributes:
        career (Career): The parent degree program.
        name (str): Display name (e.g. "Semester 3").
        number (int): Ordinal position within the career curriculum.
        year (int): Calendar year of the semester offering.
        period (str): Academic period identifier (I, II, or Summer).
        created_at (datetime): Timestamp of record creation.
    """

    class Period(models.TextChoices):
        FIRST = "I", "First"
        SECOND = "II", "Second"
        SUMMER = "SUMMER", "Summer"

    career = models.ForeignKey(
        "learning.Career",
        on_delete=models.CASCADE,
        related_name="semesters",
    )
    name = models.CharField(max_length=100)
    number = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    period = models.CharField(
        max_length=10,
        choices=Period.choices,
        default=Period.FIRST,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "semester"
        ordering = ["career", "number"]
        unique_together = [("career", "number", "year")]

    def __str__(self):
        """Return a descriptive string for this semester.

        Returns:
            str: Formatted semester identifier.
        """
        return f"{self.career.code} - {self.name} ({self.year}-{self.period})"
