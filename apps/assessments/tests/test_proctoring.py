"""Unit tests for ProctoringLog model creation and field integrity."""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.assessments.models import ProctoringLog, Quiz, QuizAttempt
from apps.learning.models import Course, LMSUser


class TestProctoringLog(TestCase):
    """Verify ProctoringLog creation with correct event_type and severity_score."""

    def setUp(self):
        """Create the prerequisite FK chain for ProctoringLog."""
        self.student = LMSUser.objects.create_user(
            username="proctor_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="aural",
        )
        course = Course.objects.create(
            name="Proctoring Course",
            code="PR-101",
            description="Course for proctoring tests.",
        )
        quiz = Quiz.objects.create(
            course=course, title="Proctored Quiz", time_limit_minutes=30
        )
        self.attempt = QuizAttempt.objects.create(
            student=self.student, quiz=quiz
        )

    def test_proctoring_log_created_with_correct_fields(self):
        """ProctoringLog is created with correct event_type and severity_score."""
        log = ProctoringLog.objects.create(
            attempt=self.attempt,
            event_type="tab_switched",
            timestamp=timezone.now(),
            severity_score=Decimal("0.85"),
        )
        self.assertEqual(log.event_type, "tab_switched")
        self.assertEqual(log.severity_score, Decimal("0.85"))
        self.assertEqual(log.attempt, self.attempt)
        self.assertEqual(ProctoringLog.objects.count(), 1)
