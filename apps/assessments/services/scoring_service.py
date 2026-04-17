import logging
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from apps.assessments.models import QuizAttempt
from apps.learning.models import Evaluation, FailedTopic, EvaluationTelemetry
from apps.learning.services import AxiomEngineClient, AxiomEngineError

logger = logging.getLogger(__name__)


class ScoringService:
    """Scores a submitted QuizAttempt, creates the corresponding Evaluation
    and FailedTopic records in the learning app, and triggers the AxiomEngine
    adaptive plan generation.

    The resulting adaptive_plan is persisted on the QuizAttempt record
    and returned in the API response for immediate consumption.
    """

    def score_and_evaluate(self, attempt: QuizAttempt) -> dict:
        """Compute the score for a QuizAttempt, persist tracking records, and request an adaptive plan.

        Args:
            attempt (QuizAttempt): The attempt record requiring scoring.

        Returns:
            dict: Scoring metrics containing score, max_score, failed_concepts,
                evaluation_id, and adaptive_plan.
        """
        attempt.end_time = timezone.now()
        answers = attempt.answers.select_related(
            "question", "selected_choice"
        ).all()

        total_questions = attempt.quiz.questions.count()
        correct_count = 0
        concept_results = defaultdict(lambda: {"correct": 0, "total": 0})

        for answer in answers:
            concept = answer.question.concept_id
            concept_results[concept]["total"] += 1
            if answer.selected_choice.is_correct:
                correct_count += 1
                concept_results[concept]["correct"] += 1

        max_score = Decimal(total_questions)
        final_score = Decimal(correct_count)

        attempt.final_score = final_score
        attempt.is_submitted = True
        attempt.save(update_fields=["final_score", "is_submitted", "end_time"])

        evaluation = Evaluation.objects.create(
            student=attempt.student,
            course=attempt.quiz.course,
            score=final_score,
            max_score=max_score,
        )

        failed_concepts = []
        for concept_id, stats in concept_results.items():
            if stats["correct"] < stats["total"]:
                FailedTopic.objects.create(
                    evaluation=evaluation,
                    concept_id=concept_id,
                    score=Decimal(stats["correct"]),
                    max_score=Decimal(stats["total"]),
                )
                failed_concepts.append(concept_id)

        duration_seconds = 0
        if attempt.end_time and attempt.start_time:
            duration_seconds = int(
                (attempt.end_time - attempt.start_time).total_seconds()
            )

        EvaluationTelemetry.objects.create(
            evaluation=evaluation,
            time_on_task_seconds=duration_seconds,
            clicks=0,
        )

        adaptive_plan = None

        if failed_concepts:
            try:
                client = AxiomEngineClient()
                adaptive_plan = client.request_adaptive_plan(evaluation.pk)
            except AxiomEngineError as exc:
                logger.warning(
                    "AxiomEngine error for eval %d: %s", evaluation.pk, exc
                )
                adaptive_plan = {"plan": [], "fallback": True}

        # Persist adaptive plan on the attempt for later retrieval
        attempt.adaptive_plan = adaptive_plan
        attempt.save(update_fields=["adaptive_plan"])

        return {
            "score": float(final_score),
            "max_score": float(max_score),
            "failed_concepts": failed_concepts,
            "evaluation_id": evaluation.pk,
            "adaptive_plan": adaptive_plan,
        }

