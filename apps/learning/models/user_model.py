from django.contrib.auth.models import AbstractUser
from django.db import models


class LMSUser(AbstractUser):
    """Platform user extended with EdTech-specific fields.

    Attributes:
        role (str): The user's role (STUDENT or TUTOR).
        vark_dominant (str): The user's dominant VARK learning modality.
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT"
        TUTOR = "TUTOR"

    class VARKProfile(models.TextChoices):
        VISUAL = "visual"
        AURAL = "aural"
        READ_WRITE = "read_write"
        KINESTHETIC = "kinesthetic"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    vark_dominant = models.CharField(
        max_length=15,
        choices=VARKProfile.choices,
        default=VARKProfile.VISUAL,
    )

    class Meta:
        db_table = "lms_user"
        verbose_name = "LMS User"
        verbose_name_plural = "LMS Users"

    def __str__(self):
        """Return ``"<username> (<role>)"``.

        Returns:
            str: Human-readable user label.
        """
        return f"{self.username} ({self.role})"
