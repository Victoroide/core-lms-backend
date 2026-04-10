from django.db import models


class Course(models.Model):
    """Academic course definition within the LMS."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "course"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} -- {self.name}"
