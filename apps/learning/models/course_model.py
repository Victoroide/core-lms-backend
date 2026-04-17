from django.db import models

from core_lms.mixins import AllObjectsManager, SoftDeleteManager, SoftDeleteMixin


class Course(SoftDeleteMixin, models.Model):
    """Academic course definition within the LMS platform architecture.

    Attributes:
        name (str): The common string reference representing the structural course configuration.
        code (str): The unique architectural identification reference identifier string.
        description (str): An extended text area describing the sequential requirements schema.
        created_at (datetime): The deterministic timestamp generated upon architectural initialization.
    """

    semester = models.ForeignKey(
        "Semester",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "course"
        ordering = ["code"]

    def __str__(self):
        """Constructs a universally standard string serialization representing the node map identity.

        Returns:
            str: The logical mapped string format sequence.
        """
        return f"{self.code} -- {self.name}"
