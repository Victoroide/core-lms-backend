from rest_framework import serializers

from apps.curriculum.models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    """Serializer for Submission CRUD operations.

    Handles student file uploads for assignments. The file field
    is backed by S3 via django-storages. Grade and graded_at are
    set by tutors via the grade action endpoint.
    """

    class Meta:
        model = Submission
        fields = [
            "id",
            "assignment",
            "student",
            "file",
            "submitted_at",
            "grade",
            "graded_at",
        ]
        read_only_fields = ["id", "submitted_at", "grade", "graded_at"]
