"""Row-level isolation tests for submission visibility across student roles."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.curriculum.models import Assignment, Submission
from apps.learning.models import Course, Lesson, LMSUser, Module


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class TestSubmissionIsolation(APITestCase):
    """Verify students see only their own submissions; tutors see all."""

    def setUp(self):
        """Create two students, a tutor, and submissions for each student."""
        self.alice = LMSUser.objects.create_user(
            username="iso_alice",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.bob = LMSUser.objects.create_user(
            username="iso_bob",
            password="testpass123",
            role="STUDENT",
            vark_dominant="aural",
        )
        self.tutor = LMSUser.objects.create_user(
            username="iso_tutor",
            password="testpass123",
            role="TUTOR",
            vark_dominant="read_write",
        )

        course = Course.objects.create(
            name="Isolation Course", code="ISO-101"
        )
        module = Module.objects.create(
            course=course, title="Isolation Module", order=1
        )
        lesson = Lesson.objects.create(
            module=module,
            title="Isolation Lesson",
            content="Test content.",
            order=1,
        )

        # Two assignments to avoid unique_together (assignment, student) collision
        assignment_1 = Assignment.objects.create(
            lesson=lesson, created_by=self.tutor, title="Assignment 1"
        )
        assignment_2 = Assignment.objects.create(
            lesson=lesson, created_by=self.tutor, title="Assignment 2"
        )

        fake_file = SimpleUploadedFile("test.txt", b"content")

        # Alice: 2 submissions (different assignments)
        Submission(
            assignment=assignment_1, student=self.alice
        ).file.save("alice_1.txt", fake_file, save=True)
        Submission(
            assignment=assignment_2, student=self.alice
        ).file.save("alice_2.txt", SimpleUploadedFile("a2.txt", b"c"), save=True)

        # Bob: 1 submission
        self.bob_submission = Submission(
            assignment=assignment_1, student=self.bob
        )
        self.bob_submission.file.save(
            "bob_1.txt", SimpleUploadedFile("b1.txt", b"c"), save=True
        )

        self.alice_token = str(
            RefreshToken.for_user(self.alice).access_token
        )
        self.bob_token = str(RefreshToken.for_user(self.bob).access_token)
        self.tutor_token = str(
            RefreshToken.for_user(self.tutor).access_token
        )

    def test_alice_sees_only_own_submissions(self):
        """Student alice sees only her own submissions (count matches)."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.alice_token}"
        )
        response = self.client.get("/api/v1/submissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_bob_sees_only_own_submissions(self):
        """Student bob sees only his own submissions (count matches)."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.bob_token}"
        )
        response = self.client.get("/api/v1/submissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_tutor_sees_all_submissions(self):
        """Tutor sees all submissions (count equals alice + bob)."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.tutor_token}"
        )
        response = self.client.get("/api/v1/submissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_alice_cannot_see_bob_submission(self):
        """GET /api/v1/submissions/{bob_id}/ as alice returns 404."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.alice_token}"
        )
        response = self.client.get(
            f"/api/v1/submissions/{self.bob_submission.pk}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_submission_returns_400(self):
        """Second submission for the same (assignment, student) returns 400."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.bob_token}"
        )
        # Bob already has one submission on assignment_1 from setUp.
        # A second POST for the same assignment must be rejected.
        bob_existing = self.bob_submission.assignment.pk
        dup_file = SimpleUploadedFile("dup.txt", b"second attempt")
        response = self.client.post(
            "/api/v1/submissions/",
            {
                "assignment": bob_existing,
                "student": self.bob.pk,
                "file": dup_file,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Response should contain a non-empty error payload
        self.assertTrue(bool(response.data))
