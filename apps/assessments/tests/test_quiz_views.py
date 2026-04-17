"""Tests for quiz list and detail endpoints."""

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.assessments.models import AnswerChoice, Question, Quiz
from apps.learning.models import Course, LMSUser


class TestQuizListDetail(APITestCase):
    """Verify quiz list and detail API behavior."""

    def setUp(self):
        """Create a quiz with questions and answer choices."""
        self.course = Course.objects.create(
            name="Quiz View Course", code="QV-101"
        )
        self.quiz = Quiz.objects.create(
            course=self.course,
            title="Quiz View Test",
            time_limit_minutes=30,
            is_active=True,
        )
        self.question = Question.objects.create(
            quiz=self.quiz, text="What is OOP?", concept_id="oop_basics", order=1
        )
        AnswerChoice.objects.create(
            question=self.question, text="Correct answer", is_correct=True
        )
        AnswerChoice.objects.create(
            question=self.question, text="Wrong answer", is_correct=False
        )

        self.student = LMSUser.objects.create_user(
            username="quiz_view_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )

    def test_quiz_list_returns_paginated_response(self):
        """GET /api/v1/quizzes/ with no token returns 200 with count and results."""
        response = self.client.get("/api/v1/quizzes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)

    def test_quiz_detail_includes_nested_questions(self):
        """GET /api/v1/quizzes/{id}/ returns nested questions with answer_choices."""
        response = self.client.get(f"/api/v1/quizzes/{self.quiz.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("questions", response.data)
        self.assertTrue(len(response.data["questions"]) > 0)
        first_question = response.data["questions"][0]
        self.assertIn("choices", first_question)

    def test_quiz_detail_hides_is_correct_from_student(self):
        """GET /api/v1/quizzes/{id}/ does not expose is_correct in answer_choices."""
        token = str(RefreshToken.for_user(self.student).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get(f"/api/v1/quizzes/{self.quiz.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for question in response.data["questions"]:
            for choice in question["choices"]:
                self.assertNotIn("is_correct", choice)
