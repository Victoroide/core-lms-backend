"""Integration tests for the full quiz submission flow via the API."""

import json
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.assessments.models import (
    AnswerChoice,
    Question,
    Quiz,
    QuizAttempt,
)
from apps.learning.models import Course, FailedTopic, LMSUser


MOCK_ADAPTIVE_PLAN = {
    "items": [{"topic": "oop_inheritance", "priority": 1}],
    "_meta": {"total_latency_ms": 42.0},
}


class TestQuizFlow(APITestCase):
    """Full quiz submission flow: create, score, FailedTopic, adaptive_plan."""

    def setUp(self):
        """Build the quiz object graph and authenticate as a student."""
        self.student = LMSUser.objects.create_user(
            username="quiz_flow_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.course = Course.objects.create(
            name="Quiz Flow Course",
            code="QF-101",
            description="Course for quiz flow tests.",
        )
        self.quiz = Quiz.objects.create(
            course=self.course,
            title="Flow Quiz",
            time_limit_minutes=30,
            is_active=True,
        )

        self.q1 = Question.objects.create(
            quiz=self.quiz, text="Q1", concept_id="oop_inheritance", order=1
        )
        AnswerChoice.objects.create(
            question=self.q1, text="Correct", is_correct=True
        )
        self.q1_wrong = AnswerChoice.objects.create(
            question=self.q1, text="Wrong", is_correct=False
        )

        self.q2 = Question.objects.create(
            quiz=self.quiz, text="Q2", concept_id="oop_polymorphism", order=2
        )
        self.q2_wrong = AnswerChoice.objects.create(
            question=self.q2, text="Wrong", is_correct=False
        )
        AnswerChoice.objects.create(
            question=self.q2, text="Correct", is_correct=True
        )

        token = str(RefreshToken.for_user(self.student).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.payload = {
            "quiz_id": self.quiz.pk,
            "student_id": self.student.pk,
            "answers": [
                {
                    "question_id": self.q1.pk,
                    "selected_choice_id": self.q1_wrong.pk,
                },
                {
                    "question_id": self.q2.pk,
                    "selected_choice_id": self.q2_wrong.pk,
                },
            ],
        }

    def _submit(self, mock_axiom_class):
        """Submit the quiz and return the response."""
        mock_axiom_class.return_value.request_adaptive_plan.return_value = (
            MOCK_ADAPTIVE_PLAN
        )
        return self.client.post(
            "/api/v1/attempts/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_submit_returns_201(self, MockAxiomClass):
        """POST /api/v1/attempts/ with wrong answers returns 201."""
        response = self._submit(MockAxiomClass)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_failed_topics_exist(self, MockAxiomClass):
        """FailedTopic records exist for the attempt after scoring."""
        self._submit(MockAxiomClass)
        self.assertTrue(
            FailedTopic.objects.filter(
                evaluation__student=self.student
            ).exists()
        )

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_adaptive_plan_stored(self, MockAxiomClass):
        """QuizAttempt.adaptive_plan is not null after scoring."""
        self._submit(MockAxiomClass)
        attempt = QuizAttempt.objects.get(student=self.student)
        self.assertIsNotNone(attempt.adaptive_plan)

    @patch("apps.assessments.services.scoring_service.AxiomEngineClient")
    def test_response_contains_adaptive_plan(self, MockAxiomClass):
        """Response body contains the adaptive_plan key."""
        response = self._submit(MockAxiomClass)
        self.assertIn("adaptive_plan", response.data)
