from rest_framework import serializers

from apps.learning.models import Module


class ModuleSerializer(serializers.ModelSerializer):
    """Serializer for Module CRUD operations.

    Represents a thematic section within a course with
    ordering and descriptive metadata.
    """

    class Meta:
        model = Module
        fields = ["id", "course", "title", "description", "order"]
        read_only_fields = ["id"]
