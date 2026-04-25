"""Unit tests for ScoringService: concept identification, FailedTopic creation,
AxiomEngine integration, and fallback behavior."""

from unittest.mock import patch

import requests
from django.test import TestCase

from apps.assessments.models import (
    AnswerChoice,
    AttemptAnswer,
    Question,
    Quiz,
    QuizAttempt,
)
from apps.assessments.services import ScoringService
from apps.learning.models import Course, Evaluation, FailedTopic, LMSUser


MOCK_ADAPTIVE_PLAN = {
    "items": [{"topic": "oop_inheritance", "priority": 1}],
    "_meta": {"total_latency_ms": 42.0},
}


def _build_quiz_graph():
    """Create the full object graph for scoring tests.

    Returns:
        tuple: (student, course, quiz, attempt, q1_wrong_choice, q2_correct_choice)
    """
    student = LMSUser.objects.create_user(
        username="scorer_student",
        password="testpass123",
        role="STUDENT",
        vark_dominant="visual",
    )
    course = Course.objects.create(
        name="Scoring Course",
        code="SC-101",
        description="Course for scoring tests.",
    )
    quiz = Quiz.objects.create(
        course=course, title="Scoring Quiz", time_limit_minutes=30
    )

    q1 = Question.objects.create(
        quiz=quiz, text="Q1", concept_id="oop_inheritance", order=1
    )
    AnswerChoice.objects.create(
        question=q1, text="Correct", is_correct=True
    )
    q1_wrong = AnswerChoice.objects.create(
        question=q1, text="Wrong", is_correct=False
    )

    q2 = Question.objects.create(
        quiz=quiz, text="Q2", concept_id="oop_polymorphism", order=2
    )
    q2_correct = AnswerChoice.objects.create(
        question=q2, text="Correct", is_correct=True
    )
    AnswerChoice.objects.create(question=q2, text="Wrong", is_correct=False)

    attempt = QuizAttempt.objects.create(student=student, quiz=quiz)

    # Student answers Q1 wrong, Q2 correct
    AttemptAnswer.objects.create(
        attempt=attempt, question=q1, selected_choice=q1_wrong
    )
    AttemptAnswer.objects.create(
        attempt=attempt, question=q2, selected_choice=q2_correct
    )

    return student, course, quiz, attempt


class TestScoringService(TestCase):
    """Verify ScoringService scoring, FailedTopic creation, and AxiomEngine calls."""

    def setUp(self):
        """Build the quiz object graph."""
        self.student, self.course, self.quiz, self.attempt = _build_quiz_graph()

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_identifies_failed_concepts(self, MockAxiomClass):
        """Correctly identifies failed concept_ids from wrong AnswerChoice selections."""
        MockAxiomClass.return_value.request_adaptive_plan.return_value = (
            MOCK_ADAPTIVE_PLAN
        )
        result = ScoringService().score_and_evaluate(self.attempt)
        self.assertIn("oop_inheritance", result["failed_concepts"])
        self.assertNotIn("oop_polymorphism", result["failed_concepts"])

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_creates_one_failed_topic_per_concept(self, MockAxiomClass):
        """Creates one FailedTopic record per failed concept_id."""
        MockAxiomClass.return_value.request_adaptive_plan.return_value = (
            MOCK_ADAPTIVE_PLAN
        )
        ScoringService().score_and_evaluate(self.attempt)
        self.assertEqual(
            FailedTopic.objects.filter(
                evaluation__student=self.student
            ).count(),
            1,
        )

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_calls_axiom_engine_client(self, MockAxiomClass):
        """Calls AxiomEngineClient.request_adaptive_plan with the evaluation pk."""
        mock_client = MockAxiomClass.return_value
        mock_client.request_adaptive_plan.return_value = MOCK_ADAPTIVE_PLAN
        ScoringService().score_and_evaluate(self.attempt)
        mock_client.request_adaptive_plan.assert_called_once()
        call_args = mock_client.request_adaptive_plan.call_args
        eval_pk = call_args[0][0]
        self.assertTrue(Evaluation.objects.filter(pk=eval_pk).exists())

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_stores_adaptive_plan_on_attempt(self, MockAxiomClass):
        """Stores the returned adaptive_plan on the QuizAttempt record."""
        MockAxiomClass.return_value.request_adaptive_plan.return_value = (
            MOCK_ADAPTIVE_PLAN
        )
        ScoringService().score_and_evaluate(self.attempt)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.adaptive_plan, MOCK_ADAPTIVE_PLAN)

    @patch("apps.learning.services.axiom_service.requests.post")
    def test_stores_fallback_on_connection_error(self, mock_post):
        """Stores fallback plan when AxiomEngine raises ConnectionError."""
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")
        ScoringService().score_and_evaluate(self.attempt)
        self.attempt.refresh_from_db()
        self.assertEqual(
            self.attempt.adaptive_plan, {"plan": [], "fallback": True}
        )
