import hashlib
import logging
from decimal import Decimal

from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone

from assessments.models import QuizAttempt
from learning.models import Certificate, Course, Evaluation, LMSUser
from learning.services.exceptions import CertificateEligibilityError

logger = logging.getLogger(__name__)


class CertificateGenerator:
    """Generates and persists course-completion certificates with SHA-256
    hash-based credential identifiers.

    Before issuing, this service verifies that the student has met the
    passing requirements for the given course (evaluation score and/or
    quiz final score above the configured threshold).
    """

    PASSING_SCORE = Decimal("60.00")

    @staticmethod
    def _compute_hash(student_id: int, course_id: int, issued_at_iso: str) -> str:
        """Generate a SHA-256 hex digest from the composite key."""
        payload = f"{student_id}:{course_id}:{issued_at_iso}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _verify_eligibility(self, student: LMSUser, course: Course) -> None:
        """Confirm the student has passed the required evaluations and/or
        quizzes for this course.

        Raises:
            CertificateEligibilityError: if the student has not met the
                minimum passing requirements.
        """
        has_passing_evaluation = Evaluation.objects.filter(
            student=student,
            course=course,
            score__gte=self.PASSING_SCORE,
        ).exists()

        has_passing_quiz = QuizAttempt.objects.filter(
            student=student,
            quiz__course=course,
            is_submitted=True,
            final_score__gte=self.PASSING_SCORE,
        ).exists()

        if not has_passing_evaluation and not has_passing_quiz:
            raise CertificateEligibilityError(
                student_id=student.pk,
                course_id=course.pk,
                reason=(
                    f"No passing evaluation or quiz attempt found "
                    f"(minimum score: {self.PASSING_SCORE})."
                ),
            )

    def issue_certificate(self, student: LMSUser, course: Course) -> Certificate:
        """Issue a certificate for the given student/course pair.

        Workflow:
            1. Verify the student has met passing requirements.
            2. Return existing certificate if one has already been issued.
            3. Compute a SHA-256 hash from (student_id, course_id, utc_now).
            4. Persist and return the Certificate record.

        Args:
            student: The LMSUser instance (must have role STUDENT).
            course: The Course instance to certify completion of.

        Returns:
            The newly created or pre-existing Certificate.

        Raises:
            CertificateEligibilityError: if the student has not passed.
        """
        self._verify_eligibility(student, course)

        existing = Certificate.objects.filter(
            student=student, course=course
        ).first()
        if existing:
            logger.info(
                "Certificate already exists: student=%d course=%d hash=%s",
                student.pk, course.pk, existing.certificate_hash,
            )
            return existing

        issued_at = timezone.now()
        cert_hash = self._compute_hash(
            student.pk, course.pk, issued_at.isoformat()
        )

        try:
            certificate = Certificate.objects.create(
                student=student,
                course=course,
                certificate_hash=cert_hash,
            )
        except IntegrityError:
            certificate = Certificate.objects.get(student=student, course=course)
            logger.warning(
                "Certificate race condition resolved: student=%d course=%d",
                student.pk, course.pk,
            )
            return certificate

        logger.info(
            "Certificate issued: student=%d course=%s hash=%s",
            student.pk, course.code, cert_hash,
        )
        return certificate
