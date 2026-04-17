from rest_framework import serializers

from apps.learning.models import Lesson


class LessonSerializer(serializers.ModelSerializer):
    """Flat serializer for Lesson CRUD operations.

    Used for list views and write operations where nested
    resource data is not required.
    """

    class Meta:
        model = Lesson
        fields = ["id", "module", "title", "content", "order"]
        read_only_fields = ["id"]


class LessonDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer that nests resources under a Lesson.

    Intended for detail views where the frontend requires
    attached resources in a single request.
    """

    resources = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "module", "title", "content", "order", "resources"]
        read_only_fields = ["id"]

    def get_resources(self, obj):
        """Return nested resource representations for this lesson.

        Args:
            obj (Lesson): The lesson instance.

        Returns:
            list[dict]: Serialized resource data.
        """
        from apps.learning.serializers.resource_serializer import ResourceSerializer

        return ResourceSerializer(obj.resources.all(), many=True).data
