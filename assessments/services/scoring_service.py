import logging
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from assessments.models import QuizAttempt
from learning.models import Evaluation, FailedTopic, EvaluationTelemetry
from learning.services import AxiomEngineClient, AxiomEngineError, AxiomEngineTimeout

logger = logging.getLogger(__name__)


class ScoringService:
    """Scores a submitted QuizAttempt, creates the corresponding Evaluation
    and FailedTopic records in the learning app, and triggers the AxiomEngine
    adaptive plan generation.
    """

    def score_and_evaluate(self, attempt: QuizAttempt) -> dict:
        """Compute the final numerical score for an operational QuizAttempt, persist relational tracking records, and trigger computational modeling.

        Args:
            attempt (QuizAttempt): The relational database target attempt sequence record requiring statistical computation.

        Returns:
            dict: The operational scoring metrics containing discrete float parameters for `score`, `max_score`, a list sequence for `failed_concepts`, the integral `evaluation_id`, and mapping pointers for `adaptive_plan` and `axiom_error` dict arrays.
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
        axiom_error = None

        if failed_concepts:
            try:
                client = AxiomEngineClient()
                adaptive_plan = client.request_adaptive_plan(evaluation.pk)
            except AxiomEngineTimeout as exc:
                logger.warning("AxiomEngine timeout for eval %d: %s", evaluation.pk, exc)
                axiom_error = {"error": "axiom_timeout", "details": str(exc)}
            except AxiomEngineError as exc:
                logger.warning("AxiomEngine error for eval %d: %s", evaluation.pk, exc)
                axiom_error = {
                    "error": "axiom_error",
                    "status_code": exc.status_code,
                    "details": exc.detail,
                }

        return {
            "score": float(final_score),
            "max_score": float(max_score),
            "failed_concepts": failed_concepts,
            "evaluation_id": evaluation.pk,
            "adaptive_plan": adaptive_plan,
            "axiom_error": axiom_error,
        }
