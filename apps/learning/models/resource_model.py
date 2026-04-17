from django.conf import settings
from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin
from apps.learning.services.storage_service import resource_upload_path


class Resource(SoftDeleteMixin, models.Model):
    """A file-based learning resource attached to a Lesson.

    Supports traditional pedagogy alongside AI quizzes by allowing
    tutors to upload syllabi, lecture videos, documents, etc.

    Attributes:
        lesson (Lesson): The parent lesson.
        uploaded_by (LMSUser): The user who uploaded the resource.
        file (File): The uploaded file stored in S3.
        resource_type (str): Categorization of the resource format.
        title (str): Human-readable resource name.
        created_at (datetime): Timestamp of upload.
    """

    class ResourceType(models.TextChoices):
        PDF = "PDF", "PDF"
        VIDEO = "VIDEO", "Video"
        DOCUMENT = "DOCUMENT", "Document"
        IMAGE = "IMAGE", "Image"
        OTHER = "OTHER", "Other"

    lesson = models.ForeignKey(
        "learning.Lesson",
        on_delete=models.CASCADE,
        related_name="resources",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_resources",
    )
    file = models.FileField(upload_to=resource_upload_path)
    resource_type = models.CharField(
        max_length=10,
        choices=ResourceType.choices,
        default=ResourceType.OTHER,
    )
    title = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "resource"
        ordering = ["-created_at"]

    def __str__(self):
        """Return a display string for the resource.

        Returns:
            str: Resource title or filename.
        """
        return self.title or self.file.name
