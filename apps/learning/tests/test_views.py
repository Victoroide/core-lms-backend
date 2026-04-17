"""Tests for learning app views: health check, token refresh, VARK onboarding."""

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.learning.models import LMSUser


class TestHealthCheck(APITestCase):
    """Verify the public health check endpoint."""

    def test_health_check_returns_200(self):
        """GET /health/ returns 200 with status ok."""
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})


class TestTokenRefresh(APITestCase):
    """Verify JWT token refresh behavior."""

    def setUp(self):
        """Create a user and obtain a refresh token."""
        self.user = LMSUser.objects.create_user(
            username="refresh_user",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.refresh = RefreshToken.for_user(self.user)

    def test_valid_refresh_token_returns_new_access_token(self):
        """POST /api/v1/auth/token/refresh/ with valid refresh returns 200 with access key."""
        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": str(self.refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_invalid_refresh_token_returns_401(self):
        """POST /api/v1/auth/token/refresh/ with invalid token returns 401."""
        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": "invalid-garbage-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_blacklisted_after_rotation(self):
        """Rotated refresh token must be blacklisted on second use."""
        # First use: succeeds and returns a new refresh token
        first_response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": str(self.refresh)},
            format="json",
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        # Second use of the same (now-blacklisted) refresh token must fail
        second_response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": str(self.refresh)},
            format="json",
        )
        self.assertEqual(
            second_response.status_code, status.HTTP_401_UNAUTHORIZED
        )


class TestTokenRateLimit(APITestCase):
    """Verify the token endpoint rejects brute-force attempts with 429."""

    def test_token_endpoint_rate_limit(self):
        """POST /api/v1/auth/token/ 11 times triggers a 429 response."""
        payload = {"username": "nonexistent", "password": "wrong"}
        # First 10 attempts are allowed (but return 401 for bad credentials)
        for _ in range(10):
            response = self.client.post(
                "/api/v1/auth/token/", payload, format="json"
            )
            self.assertIn(
                response.status_code,
                (status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST),
            )
        # 11th attempt must be rate-limited
        response = self.client.post(
            "/api/v1/auth/token/", payload, format="json"
        )
        self.assertEqual(
            response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )


class TestVARKOnboarding(APITestCase):
    """Verify VARK onboarding endpoint behavior."""

    def setUp(self):
        """Create student and tutor with JWT tokens."""
        self.student = LMSUser.objects.create_user(
            username="vark_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="aural",
        )
        self.other_student = LMSUser.objects.create_user(
            username="vark_other",
            password="testpass123",
            role="STUDENT",
            vark_dominant="aural",
        )
        self.student_token = str(
            RefreshToken.for_user(self.student).access_token
        )
        self.other_token = str(
            RefreshToken.for_user(self.other_student).access_token
        )

    def test_student_can_update_vark(self):
        """POST /api/v1/users/{id}/onboard/ updates vark_dominant to visual."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.student_token}"
        )
        response = self.client.post(
            f"/api/v1/users/{self.student.pk}/onboard/",
            {
                "answers": [
                    {"category": "visual", "value": 9},
                    {"category": "aural", "value": 2},
                    {"category": "read_write", "value": 3},
                    {"category": "kinesthetic", "value": 1},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["vark_dominant"], "visual")

    def test_invalid_vark_value_returns_400(self):
        """POST with invalid category returns 400."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.student_token}"
        )
        response = self.client.post(
            f"/api/v1/users/{self.student.pk}/onboard/",
            {"answers": [{"category": "invalid", "value": 5}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_user_cannot_update_vark(self):
        """POST to a different user's onboard endpoint returns 403."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.other_token}"
        )
        response = self.client.post(
            f"/api/v1/users/{self.student.pk}/onboard/",
            {
                "answers": [
                    {"category": "visual", "value": 9},
                    {"category": "aural", "value": 2},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
