"""Tests for quiz attempt retrieval and list scoping."""

import json
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.assessments.models import AnswerChoice, Question, Quiz
from apps.learning.models import Course, LMSUser


MOCK_ADAPTIVE_PLAN = {
    "items": [{"topic": "oop_inheritance", "priority": 1}],
    "_meta": {"total_latency_ms": 42.0},
}


class TestAttemptRetrieval(APITestCase):
    """Verify attempt list and retrieve scoped to the authenticated student."""

    def setUp(self):
        """Create two students, a quiz, and submit an attempt for each."""
        self.student_a = LMSUser.objects.create_user(
            username="attempt_student_a",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.student_b = LMSUser.objects.create_user(
            username="attempt_student_b",
            password="testpass123",
            role="STUDENT",
            vark_dominant="aural",
        )
        self.course = Course.objects.create(
            name="Attempt Course", code="AT-101"
        )
        self.quiz = Quiz.objects.create(
            course=self.course,
            title="Attempt Quiz",
            time_limit_minutes=30,
            is_active=True,
        )
        q = Question.objects.create(
            quiz=self.quiz, text="Q1", concept_id="q1", order=1
        )
        AnswerChoice.objects.create(
            question=q, text="Correct", is_correct=True
        )
        self.wrong = AnswerChoice.objects.create(
            question=q, text="Wrong", is_correct=False
        )

        self.token_a = str(
            RefreshToken.for_user(self.student_a).access_token
        )
        self.token_b = str(
            RefreshToken.for_user(self.student_b).access_token
        )

        # Submit an attempt for student A
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        with patch(
            "apps.assessments.services.scoring_service.AxiomEngineClient"
        ) as MockAxiom:
            MockAxiom.return_value.request_adaptive_plan.return_value = (
                MOCK_ADAPTIVE_PLAN
            )
            resp = self.client.post(
                "/api/v1/attempts/",
                data=json.dumps({
                    "quiz_id": self.quiz.pk,
                    "student_id": self.student_a.pk,
                    "answers": [
                        {
                            "question_id": q.pk,
                            "selected_choice_id": self.wrong.pk,
                        }
                    ],
                }),
                content_type="application/json",
            )
        self.attempt_a_id = resp.data["id"]

        # Submit an attempt for student B
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        with patch(
            "apps.assessments.services.scoring_service.AxiomEngineClient"
        ) as MockAxiom:
            MockAxiom.return_value.request_adaptive_plan.return_value = (
                MOCK_ADAPTIVE_PLAN
            )
            resp = self.client.post(
                "/api/v1/attempts/",
                data=json.dumps({
                    "quiz_id": self.quiz.pk,
                    "student_id": self.student_b.pk,
                    "answers": [
                        {
                            "question_id": q.pk,
                            "selected_choice_id": self.wrong.pk,
                        }
                    ],
                }),
                content_type="application/json",
            )
        self.attempt_b_id = resp.data["id"]

    def test_student_can_retrieve_own_attempt(self):
        """GET /api/v1/attempts/{id}/ returns 200 with adaptive_plan for own attempt."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(f"/api/v1/attempts/{self.attempt_a_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("adaptive_plan", response.data)
        self.assertIsNotNone(response.data["adaptive_plan"])

    def test_student_cannot_retrieve_other_student_attempt(self):
        """GET another student's attempt returns 404."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(f"/api/v1/attempts/{self.attempt_b_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_attempt_list_scoped_to_student(self):
        """GET /api/v1/attempts/ returns only the authenticated student's attempts."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get("/api/v1/attempts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for attempt in response.data["results"]:
            self.assertEqual(attempt["student"], self.student_a.pk)
