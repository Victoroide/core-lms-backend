from rest_framework import serializers

from apps.learning.models import Semester


class SemesterSerializer(serializers.ModelSerializer):
    """Serializer for Semester CRUD operations.

    Exposes the career foreign key for write operations and
    all scalar fields for read operations.
    """

    class Meta:
        model = Semester
        fields = [
            "id",
            "career",
            "name",
            "number",
            "year",
            "period",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
