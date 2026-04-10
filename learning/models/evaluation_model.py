from django.conf import settings
from django.db import models


class Evaluation(models.Model):
    """Dynamically parses and records a standard target assessment configuration matrix structure.

    Attributes:
        student (LMSUser): The relational pointer configuring the explicit mapped student structure assignment logic.
        course (Course): The primary key mapped configuration identifying the testing boundary parameter target point.
        score (Decimal): The standard decimal formatted outcome integer metrics configuration score mapping array.
        max_score (Decimal): The deterministic scalar structural outcome maximum threshold score constraint property point parameters.
        created_at (datetime): The UTC-aligned relational timestamp sequence mapping.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    course = models.ForeignKey(
        "learning.Course",
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluation"
        ordering = ["-created_at"]

    def __str__(self):
        """Computes a structural debug evaluation reference array formatted target string pointer property mapping segment map.

        Returns:
            str: The structured JSON component topological mapping output.
        """
        return f"Eval#{self.pk} {self.student} - {self.course.code} ({self.score}/{self.max_score})"
