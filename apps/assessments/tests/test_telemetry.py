"""Tests for EvaluationTelemetry endpoint."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.learning.models import (
    Course,
    Evaluation,
    EvaluationTelemetry,
    LMSUser,
)


class TestEvaluationTelemetry(APITestCase):
    """Verify EvaluationTelemetry create and list behavior."""

    def setUp(self):
        """Create student, tutor, evaluation, and JWT tokens."""
        self.student = LMSUser.objects.create_user(
            username="telem_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.other_student = LMSUser.objects.create_user(
            username="telem_other",
            password="testpass123",
            role="STUDENT",
            vark_dominant="aural",
        )
        self.tutor = LMSUser.objects.create_user(
            username="telem_tutor",
            password="testpass123",
            role="TUTOR",
            vark_dominant="read_write",
        )
        self.course = Course.objects.create(
            name="Telemetry Course", code="TL-101"
        )
        self.eval_mine = Evaluation.objects.create(
            student=self.student,
            course=self.course,
            score=Decimal("80.00"),
            max_score=Decimal("100.00"),
        )
        self.eval_other = Evaluation.objects.create(
            student=self.other_student,
            course=self.course,
            score=Decimal("70.00"),
            max_score=Decimal("100.00"),
        )
        # Pre-create telemetry for the other student
        EvaluationTelemetry.objects.create(
            evaluation=self.eval_other,
            time_on_task_seconds=500,
            clicks=20,
        )
        self.student_token = str(
            RefreshToken.for_user(self.student).access_token
        )
        self.tutor_token = str(
            RefreshToken.for_user(self.tutor).access_token
        )

    def test_student_can_create_telemetry(self):
        """POST /api/v1/evaluation-telemetry/ as student returns 201."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.student_token}"
        )
        response = self.client.post(
            "/api/v1/evaluation-telemetry/",
            {
                "evaluation": self.eval_mine.pk,
                "time_on_task_seconds": 1200,
                "clicks": 45,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_tutor_can_list_telemetry(self):
        """GET /api/v1/evaluation-telemetry/ as tutor returns 200 with paginated results."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        response = self.client.get("/api/v1/evaluation-telemetry/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)

    def test_student_cannot_list_others_telemetry(self):
        """GET /api/v1/evaluation-telemetry/ as student returns only own records."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.student_token}"
        )
        response = self.client.get("/api/v1/evaluation-telemetry/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Student has no telemetry records yet (the pre-created one belongs to other_student)
        self.assertEqual(response.data["count"], 0)
