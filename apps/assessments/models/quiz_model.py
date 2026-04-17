from django.db import models


class Quiz(models.Model):
    """A timed assessment instrument linked to a specific course."""

    course = models.ForeignKey(
        "learning.Course",
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    time_limit_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quiz"
        verbose_name_plural = "Quizzes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.course.code})"


class Question(models.Model):
    """A single question within a quiz. The concept_id field maps directly
    to a node name in the AxiomEngine knowledge graph, enabling automatic
    identification of failed concepts after scoring.
    """

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    concept_id = models.CharField(
        max_length=100,
        help_text="Must match a node name in the AxiomEngine knowledge graph.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "question"
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class AnswerChoice(models.Model):
    """One of several possible answers for a question. Exactly one choice
    per question must have is_correct=True.
    """

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "answer_choice"

    def __str__(self):
        marker = "[CORRECT]" if self.is_correct else ""
        return f"{self.text[:60]} {marker}"
