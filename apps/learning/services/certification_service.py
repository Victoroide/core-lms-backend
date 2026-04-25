import hashlib
import logging
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from apps.assessments.models import QuizAttempt
from apps.learning.models import Certificate, Course, Evaluation, LMSUser
from apps.learning.services.exceptions import CertificateEligibilityError

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
        """Compute the SHA-256 hex digest used as the certificate identifier.

        Args:
            student_id (int): Primary key of the LMSUser receiving the certificate.
            course_id (int): Primary key of the certified Course.
            issued_at_iso (str): ISO-8601 timestamp of issuance.

        Returns:
            str: 64-character SHA-256 hexadecimal digest.
        """
        payload = f"{student_id}:{course_id}:{issued_at_iso}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _verify_eligibility(self, student: LMSUser, course: Course) -> None:
        """Confirm ``student`` has met the passing threshold for ``course``.

        Args:
            student (LMSUser): The student under verification.
            course (Course): The target course.

        Raises:
            CertificateEligibilityError: If the student has not met the
                minimum passing score on either an Evaluation or a QuizAttempt.
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
        """Issue (or return the existing) certificate for ``student`` in ``course``.

        Workflow:
            1. Verify the student meets the passing threshold.
            2. Return the existing certificate if one already exists.
            3. Derive a new SHA-256 hash for the certificate identifier.
            4. Persist and return the resulting Certificate row.

        Args:
            student (LMSUser): The student being certified (must be a STUDENT).
            course (Course): The course being certified.

        Returns:
            Certificate: The newly created or pre-existing certificate row.

        Raises:
            CertificateEligibilityError: If the student has not met the
                passing criteria for this course.
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
