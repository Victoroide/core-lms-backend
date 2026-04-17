from rest_framework import serializers

from apps.curriculum.models import Assignment


class AssignmentSerializer(serializers.ModelSerializer):
    """Serializer for Assignment CRUD operations.

    Supports tutor-created lesson assignments with due dates
    and maximum score configuration. The lesson FK references
    a learning.Lesson instance.
    """

    class Meta:
        model = Assignment
        fields = [
            "id",
            "lesson",
            "created_by",
            "title",
            "description",
            "due_date",
            "max_score",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
