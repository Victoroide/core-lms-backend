from django.conf import settings
from django.db import models


class QuizAttempt(models.Model):
    """Records a student's attempt at a specific quiz, including timing
    and the computed final score after submission.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    quiz = models.ForeignKey(
        "assessments.Quiz",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    final_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    is_submitted = models.BooleanField(default=False)

    class Meta:
        db_table = "quiz_attempt"
        ordering = ["-start_time"]

    def __str__(self):
        return f"Attempt#{self.pk} {self.student} - {self.quiz.title}"


class AttemptAnswer(models.Model):
    """Links a student's selected answer choice to a specific question
    within an attempt. Used by the scoring service to compute results.
    """

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        "assessments.Question",
        on_delete=models.CASCADE,
        related_name="attempt_answers",
    )
    selected_choice = models.ForeignKey(
        "assessments.AnswerChoice",
        on_delete=models.CASCADE,
        related_name="selections",
    )

    class Meta:
        db_table = "attempt_answer"
        unique_together = [("attempt", "question")]

    def __str__(self):
        return f"Attempt#{self.attempt_id} Q#{self.question_id}"
