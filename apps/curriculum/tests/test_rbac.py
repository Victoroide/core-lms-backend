"""RBAC tests: verify IsStudent and IsTutor permission enforcement."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.curriculum.models import Assignment
from apps.learning.models import Course, Lesson, LMSUser, Module


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class TestRBAC(APITestCase):
    """Verify role-based access control for assignments and submissions."""

    def setUp(self):
        """Create users, academic hierarchy, and JWT tokens."""
        self.student = LMSUser.objects.create_user(
            username="rbac_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.tutor = LMSUser.objects.create_user(
            username="rbac_tutor",
            password="testpass123",
            role="TUTOR",
            vark_dominant="read_write",
        )
        self.course = Course.objects.create(
            name="RBAC Course", code="RBAC-101"
        )
        module = Module.objects.create(
            course=self.course, title="RBAC Module", order=1
        )
        self.lesson = Lesson.objects.create(
            module=module, title="RBAC Lesson", content="Test content.", order=1
        )
        self.assignment = Assignment.objects.create(
            lesson=self.lesson, created_by=self.tutor, title="RBAC Assignment"
        )

        self.student_token = str(
            RefreshToken.for_user(self.student).access_token
        )
        self.tutor_token = str(
            RefreshToken.for_user(self.tutor).access_token
        )

    def test_student_can_post_submission(self):
        """IsStudent permission allows student to POST a submission."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.student_token}"
        )
        fake_file = SimpleUploadedFile(
            "test.pdf", b"fake content", content_type="application/pdf"
        )
        response = self.client.post(
            "/api/v1/submissions/",
            {
                "assignment": self.assignment.pk,
                "student": self.student.pk,
                "file": fake_file,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_tutor_cannot_post_submission(self):
        """IsStudent permission denies tutor from POSTing a submission."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        fake_file = SimpleUploadedFile(
            "test.pdf", b"fake content", content_type="application/pdf"
        )
        response = self.client.post(
            "/api/v1/submissions/",
            {
                "assignment": self.assignment.pk,
                "student": self.tutor.pk,
                "file": fake_file,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tutor_can_post_assignment(self):
        """IsTutor permission allows tutor to POST an assignment."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        response = self.client.post(
            "/api/v1/assignments/",
            {
                "lesson": self.lesson.pk,
                "title": "New Assignment",
                "description": "Test assignment.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_cannot_post_assignment(self):
        """IsTutor permission denies student from POSTing an assignment."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.student_token}"
        )
        response = self.client.post(
            "/api/v1/assignments/",
            {
                "lesson": self.lesson.pk,
                "title": "Forbidden Assignment",
                "description": "Should fail.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request to a protected endpoint returns 401."""
        self.client.credentials()
        response = self.client.get("/api/v1/submissions/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
