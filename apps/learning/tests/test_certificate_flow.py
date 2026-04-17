"""Integration tests for the certificate generation flow via the API."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.learning.models import Certificate, Course, Evaluation, LMSUser


class TestCertificateFlow(APITestCase):
    """Full certificate generation flow via POST /api/v1/certificates/generate/."""

    def setUp(self):
        """Create a student with a passing evaluation and authenticate."""
        self.student = LMSUser.objects.create_user(
            username="cert_flow_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="kinesthetic",
        )
        self.course = Course.objects.create(
            name="Cert Flow Course",
            code="CF-101",
            description="Course for certificate flow tests.",
        )
        Evaluation.objects.create(
            student=self.student,
            course=self.course,
            score=Decimal("80.00"),
            max_score=Decimal("100.00"),
        )
        token = str(RefreshToken.for_user(self.student).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _generate(self):
        """POST to the certificate generate endpoint."""
        return self.client.post(
            "/api/v1/certificates/generate/",
            {
                "student_id": self.student.pk,
                "course_id": self.course.pk,
            },
            format="json",
        )

    def test_generate_returns_201(self):
        """POST /api/v1/certificates/generate/ returns 201 for eligible student."""
        response = self._generate()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_certificate_hash_length_64(self):
        """certificate_hash length equals 64 characters."""
        response = self._generate()
        self.assertEqual(len(response.data["certificate_hash"]), 64)

    def test_certificate_exists_in_db(self):
        """Certificate record exists in the database after generation."""
        self._generate()
        self.assertTrue(
            Certificate.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )
