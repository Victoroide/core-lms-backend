"""Tests for course detail nested response and soft-delete filtering."""

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.learning.models import Course, Lesson, LMSUser, Module


class TestCourseNestedDetail(APITestCase):
    """Verify course detail returns nested modules, lessons, and resources."""

    def setUp(self):
        """Create course with module, lesson, and authenticate."""
        self.tutor = LMSUser.objects.create_user(
            username="course_detail_tutor",
            password="testpass123",
            role="TUTOR",
            vark_dominant="read_write",
        )
        self.course = Course.objects.create(
            name="Nested Course", code="NC-101"
        )
        self.module = Module.objects.create(
            course=self.course, title="Module 1", order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Lesson 1",
            content="Content.",
            order=1,
        )
        token = str(RefreshToken.for_user(self.tutor).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_course_detail_returns_nested_modules_and_lessons(self):
        """GET /api/v1/courses/{id}/ returns modules with nested lessons."""
        response = self.client.get(f"/api/v1/courses/{self.course.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("modules", response.data)
        self.assertTrue(len(response.data["modules"]) > 0)
        first_module = response.data["modules"][0]
        self.assertIn("lessons", first_module)
        self.assertTrue(len(first_module["lessons"]) > 0)

    def test_course_detail_excludes_soft_deleted_module(self):
        """Soft-deleted module is absent from course detail response."""
        self.module.delete()
        response = self.client.get(f"/api/v1/courses/{self.course.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["modules"]), 0)
