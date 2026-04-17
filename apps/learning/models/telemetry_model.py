from django.db import models


class EvaluationTelemetry(models.Model):
    """Client-side behavioral telemetry captured during an evaluation session."""

    evaluation = models.OneToOneField(
        "learning.Evaluation",
        on_delete=models.CASCADE,
        related_name="telemetry",
    )
    time_on_task_seconds = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "evaluation_telemetry"
        verbose_name_plural = "Evaluation Telemetry"

    def __str__(self):
        return f"Telemetry for Eval#{self.evaluation_id}"
