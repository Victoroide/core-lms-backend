from django.conf import settings
from django.db import models


class Certificate(models.Model):
    """Issued when a student satisfactorily completes a course. The
    certificate_hash is a SHA-256 hex digest computed by CertificationService
    from the composite key (student_id, course_id, issued_at).
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    course = models.ForeignKey(
        "learning.Course",
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        blank=True,
        default="",
    )

    class Meta:
        db_table = "certificate"
        unique_together = [("student", "course")]
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Cert {self.certificate_hash[:12]}... - {self.student} / {self.course.code}"
