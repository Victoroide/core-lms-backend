from django.db import models


class ProctoringLog(models.Model):
    """Anti-cheat telemetry event captured by the frontend proctoring system
    (face-api.js or tab-visibility API). Stored per-attempt for post-hoc
    integrity analysis.
    """

    class EventType(models.TextChoices):
        TAB_SWITCHED = "tab_switched"
        FACE_NOT_DETECTED = "face_not_detected"
        MULTIPLE_FACES = "multiple_faces"

    attempt = models.ForeignKey(
        "assessments.QuizAttempt",
        on_delete=models.CASCADE,
        related_name="proctoring_logs",
    )
    event_type = models.CharField(
        max_length=25,
        choices=EventType.choices,
    )
    timestamp = models.DateTimeField()
    severity_score = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.00
    )

    class Meta:
        db_table = "proctoring_log"
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.event_type} @ {self.timestamp} (attempt={self.attempt_id})"
