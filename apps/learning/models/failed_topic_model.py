from django.db import models


class FailedTopic(models.Model):
    """A concept the student failed within an evaluation.
    concept_id must match a node name in the AxiomEngine knowledge graph.
    """

    evaluation = models.ForeignKey(
        "learning.Evaluation",
        on_delete=models.CASCADE,
        related_name="failed_topics",
    )
    concept_id = models.CharField(max_length=100)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        db_table = "failed_topic"

    def __str__(self):
        return f"{self.concept_id} ({self.score}/{self.max_score})"
