import hashlib
import logging
from decimal import Decimal

from django.db import IntegrityError
from django.db.models import Q
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
        """Generate a secure SHA-256 hexadecimal digest from the composite credential key.

        Args:
            student_id (int): The primary key of the LMSUser acquiring the certification.
            course_id (int): The primary key of the Course entity being certified.
            issued_at_iso (str): The ISO-8601 formatted temporal timestamp of the issuance operation.

        Returns:
            str: The 64-character SHA-256 hexadecimal cryptographic digest sequence.
        """
        payload = f"{student_id}:{course_id}:{issued_at_iso}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _verify_eligibility(self, student: LMSUser, course: Course) -> None:
        """Confirm the student entity has satisfied the threshold evaluations or quizzes for this course.

        Args:
            student (LMSUser): The student user node entity under verification logic.
            course (Course): The target course node entity.

        Raises:
            CertificateEligibilityError: If the user entity has failed to satisfy the minimum established passing constraints parameters.
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
        """Authoritatively issue a verifiable cryptographic certificate for a student mapping pair.

        Workflow sequence:
            1. Transpose verification protocol over the student's passing threshold conditions.
            2. Safely return the pre-existing certification token if one has previously been authored.
            3. Cryptographically derive a new SHA-256 secure hash token sequence mapping.
            4. Persist and return the resulting Certificate database relational record.

        Args:
            student (LMSUser): The LMSUser operational instance (requires the structural role mapping parameter variant STUDENT).
            course (Course): The designated Course operational structural instance designated to certify completion logic against.

        Returns:
            Certificate: The newly committed relational database record or the preexisting Certificate object instance.

        Raises:
            CertificateEligibilityError: If the operational student target entity sequence has not fulfilled passing criterion protocols.
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
