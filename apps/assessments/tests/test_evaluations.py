"""Tests for Evaluation CRUD endpoints."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.learning.models import Course, Evaluation, LMSUser


class TestEvaluationCRUD(APITestCase):
    """Verify Evaluation list, detail, create, and update endpoints."""

    def setUp(self):
        """Create users, course, evaluation, and JWT tokens."""
        self.student = LMSUser.objects.create_user(
            username="eval_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.tutor = LMSUser.objects.create_user(
            username="eval_tutor",
            password="testpass123",
            role="TUTOR",
            vark_dominant="read_write",
        )
        self.course = Course.objects.create(
            name="Eval Course", code="EV-101"
        )
        self.evaluation = Evaluation.objects.create(
            student=self.student,
            course=self.course,
            score=Decimal("75.00"),
            max_score=Decimal("100.00"),
        )
        self.student_token = str(
            RefreshToken.for_user(self.student).access_token
        )
        self.tutor_token = str(
            RefreshToken.for_user(self.tutor).access_token
        )

    def test_create_evaluation_authenticated(self):
        """POST /api/v1/evaluations/ as authenticated user returns 201."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        response = self.client.post(
            "/api/v1/evaluations/",
            {
                "student": self.student.pk,
                "course": self.course.pk,
                "score": "85.00",
                "max_score": "100.00",
                "failed_topics": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_evaluation_list_paginated(self):
        """GET /api/v1/evaluations/ returns paginated response with count and results."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        response = self.client.get("/api/v1/evaluations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)

    def test_evaluation_detail_returns_score(self):
        """GET /api/v1/evaluations/{id}/ returns score and max_score."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        response = self.client.get(
            f"/api/v1/evaluations/{self.evaluation.pk}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("score", response.data)
        self.assertIn("max_score", response.data)

    def test_update_evaluation_as_tutor(self):
        """PATCH /api/v1/evaluations/{id}/ updates the score."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        response = self.client.patch(
            f"/api/v1/evaluations/{self.evaluation.pk}/",
            {"score": "90.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], "90.00")

    def test_unauthenticated_evaluation_returns_401(self):
        """GET /api/v1/evaluations/ with no token returns 401."""
        self.client.credentials()
        response = self.client.get("/api/v1/evaluations/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_evaluation_telemetry_linked_to_evaluation(self):
        """POST /api/v1/evaluation-telemetry/ persists the evaluation FK."""
        # Create a new evaluation (setUp's already has telemetry via other tests flow)
        new_eval = Evaluation.objects.create(
            student=self.student,
            course=self.course,
            score=Decimal("70.00"),
            max_score=Decimal("100.00"),
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.student_token}"
        )
        create_response = self.client.post(
            "/api/v1/evaluation-telemetry/",
            {
                "evaluation": new_eval.pk,
                "time_on_task_seconds": 450,
                "clicks": 35,
            },
            format="json",
        )
        self.assertEqual(
            create_response.status_code, status.HTTP_201_CREATED
        )
        telemetry_id = create_response.data["id"]

        get_response = self.client.get(
            f"/api/v1/evaluation-telemetry/{telemetry_id}/"
        )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["evaluation"], new_eval.pk)
