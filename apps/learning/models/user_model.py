from django.contrib.auth.models import AbstractUser
from django.db import models


class LMSUser(AbstractUser):
    """Platform user configuration object extended with explicit EdTech-specific parametric fields.

    Attributes:
        role (str): The relational operational role logic string.
        vark_dominant (str): The explicitly defined overriding target learning modality logic sequence.
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
        """Generates a standard mapping identification pointer string format component.

        Returns:
            str: The mapped entity text identity array logic.
        """
        return f"{self.username} ({self.role})"
