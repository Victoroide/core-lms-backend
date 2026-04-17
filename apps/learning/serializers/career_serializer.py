from rest_framework import serializers

from apps.learning.models import Career


class CareerSerializer(serializers.ModelSerializer):
    """Flat serializer for Career CRUD operations.

    Used for list views and write operations where nested
    semester data is not required.
    """

    class Meta:
        model = Career
        fields = ["id", "name", "code", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class CareerDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer that nests semesters under a Career.

    Intended for detail views where the frontend requires
    the full career → semester hierarchy in a single request.
    """

    semesters = serializers.SerializerMethodField()

    class Meta:
        model = Career
        fields = ["id", "name", "code", "description", "created_at", "semesters"]
        read_only_fields = ["id", "created_at"]

    def get_semesters(self, obj):
        """Return nested semester representations for this career.

        Args:
            obj (Career): The career instance.

        Returns:
            list[dict]: Serialized semester data.
        """
        from apps.learning.serializers.semester_serializer import SemesterSerializer

        return SemesterSerializer(obj.semesters.all(), many=True).data
