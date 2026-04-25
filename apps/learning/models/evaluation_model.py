from django.conf import settings
from django.db import models


class Evaluation(models.Model):
    """Persisted record of a single assessment outcome for a student in a course.

    Attributes:
        student (LMSUser): The student to whom this evaluation belongs.
        course (Course): The course this evaluation is scoped to.
        score (Decimal): The score the student obtained.
        max_score (Decimal): The maximum score available for this evaluation.
        created_at (datetime): UTC timestamp set when the record is created.
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
        """Return a debug label of the form ``Eval#<pk> <student> - <code> (s/max)``.

        Returns:
            str: Human-readable evaluation label.
        """
        return (
            f"Eval#{self.pk} {self.student} - {self.course.code} "
            f"({self.score}/{self.max_score})"
        )
