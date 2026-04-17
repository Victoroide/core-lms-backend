from django.conf import settings
from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin
from apps.curriculum.services.storage_service import submission_upload_path


class Submission(SoftDeleteMixin, models.Model):
    """A student-uploaded file submission for a specific Assignment.

    Supports the file-based assessment workflow where students upload
    deliverables and tutors grade them.

    Attributes:
        assignment (Assignment): The parent assignment.
        student (LMSUser): The student who submitted.
        file (File): The uploaded submission file stored in S3.
        submitted_at (datetime): Timestamp of submission.
        grade (Decimal): Tutor-assigned grade (nullable until graded).
        graded_at (datetime): Timestamp of grading (nullable until graded).
    """

    assignment = models.ForeignKey(
        "curriculum.Assignment",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    file = models.FileField(upload_to=submission_upload_path)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "submission"
        ordering = ["-submitted_at"]
        unique_together = [("assignment", "student")]

    def __str__(self):
        """Return a display string for the submission.

        Returns:
            str: Submission identifier with student and assignment.
        """
        return f"Submission#{self.pk} {self.student} - {self.assignment.title}"
