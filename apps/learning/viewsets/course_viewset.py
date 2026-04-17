from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning.models import Course
from apps.learning.permissions import IsTutor
from apps.learning.serializers import CourseListSerializer, CourseDetailSerializer


class CourseViewSet(viewsets.ModelViewSet):
    """CRUD for Course entities with semester/career filtering.

    Supports filtering by semester and semester__career via query
    parameters. The detail action returns a fully nested hierarchy
    (semester, modules, lessons, resources) using prefetch_related
    to prevent N+1 queries.

    **Requires authentication.**
    """

    queryset = Course.objects.select_related("semester__career").all()
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["semester", "semester__career", "is_deleted"]

    def get_permissions(self):
        """Restrict mutation operations to tutors.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List courses",
        operation_description=(
            "Returns a paginated list of courses. "
            "Filter by ?semester=<id> or ?semester__career=<id>."
        ),
        tags=["Academic Ontology"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of course records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized course data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a course with full hierarchy",
        operation_description=(
            "Returns a single course with nested semester, modules, "
            "lessons, and resources. Optimized with prefetch_related."
        ),
        tags=["Academic Ontology"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single course with the full nested hierarchy.

        Overrides the default queryset to prefetch the complete
        module → lesson → resource tree in a single database round-trip.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized course data with nested hierarchy.
        """
        instance = self.get_object()
        instance = (
            Course.objects
            .select_related("semester__career")
            .prefetch_related("modules__lessons__resources")
            .get(pk=instance.pk)
        )
        serializer = CourseDetailSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create a course",
        operation_description="Creates a new course. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new course record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized course data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a course",
        operation_description="Full update of a course. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a course record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated course data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update a course",
        operation_description="Partial update of a course. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a course record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated course data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete a course",
        operation_description="Soft-deletes a course (marks is_deleted=True). Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete a course record instead of issuing a SQL DELETE.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: HTTP 204 No Content.
        """
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
