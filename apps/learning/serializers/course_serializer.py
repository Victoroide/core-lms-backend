from rest_framework import serializers

from apps.learning.models import Course
from apps.learning.serializers.module_serializer import ModuleSerializer
from apps.learning.serializers.semester_serializer import SemesterSerializer


class CourseListSerializer(serializers.ModelSerializer):
    """Flat serializer for Course list and write operations.

    Exposes the semester FK for filtering and assignment.
    Used where nested module/lesson data is not required.
    """

    class Meta:
        model = Course
        fields = ["id", "semester", "name", "code", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class CourseDetailSerializer(serializers.ModelSerializer):
    """Read-only nested serializer returning the full course hierarchy.

    Nests semester info, modules, and their lessons to provide
    the frontend with the complete course structure in a single
    request. The viewset queryset must use select_related and
    prefetch_related to avoid N+1 queries.
    """

    semester = SemesterSerializer(read_only=True)
    modules = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "semester",
            "name",
            "code",
            "description",
            "created_at",
            "modules",
        ]
        read_only_fields = ["id", "created_at"]

    def get_modules(self, obj):
        """Return nested module representations with their lessons.

        Args:
            obj (Course): The course instance.

        Returns:
            list[dict]: Serialized module data with nested lessons.
        """
        from apps.learning.serializers.lesson_serializer import LessonDetailSerializer

        modules = obj.modules.all()
        result = []
        for module in modules:
            module_data = ModuleSerializer(module).data
            module_data["lessons"] = LessonDetailSerializer(
                module.lessons.all(), many=True
            ).data
            result.append(module_data)
        return result
