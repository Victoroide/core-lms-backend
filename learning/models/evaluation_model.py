from django.conf import settings
from django.db import models


class Evaluation(models.Model):
    """Records a student's assessment attempt for a specific course."""

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
        return f"Eval#{self.pk} {self.student} - {self.course.code} ({self.score}/{self.max_score})"
