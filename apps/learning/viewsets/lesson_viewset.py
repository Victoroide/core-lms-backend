from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning.models import Lesson
from apps.learning.permissions import IsTutor
from apps.learning.serializers import LessonSerializer, LessonDetailSerializer


class LessonViewSet(viewsets.ModelViewSet):
    """CRUD for Lesson entities (teaching units within a Module).

    Supports filtering by module via the ?module query parameter.
    List and retrieve are available to any authenticated user.
    Create, update, and delete are restricted to tutors.

    **Requires authentication.**
    """

    queryset = Lesson.objects.select_related("module__course").all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["module", "is_deleted"]

    def get_serializer_class(self):
        """Return the appropriate serializer based on the action.

        Returns:
            type: LessonDetailSerializer for retrieve, LessonSerializer otherwise.
        """
        if self.action == "retrieve":
            return LessonDetailSerializer
        return LessonSerializer

    def get_permissions(self):
        """Restrict mutation operations to tutors.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List lessons",
        operation_description="Returns a paginated list of lessons. Filter by ?module=<id>.",
        tags=["Academic Ontology"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of lesson records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized lesson data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a lesson with resources",
        operation_description="Returns a single lesson with nested resources.",
        tags=["Academic Ontology"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single lesson with nested resource data.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized lesson data with nested resources.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a lesson",
        operation_description="Creates a new lesson within a module. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new lesson record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized lesson data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a lesson",
        operation_description="Full update of a lesson. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a lesson record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated lesson data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update a lesson",
        operation_description="Partial update of a lesson. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a lesson record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated lesson data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete a lesson",
        operation_description=(
            "Soft-deletes a lesson (marks is_deleted=True). Restricted to tutors."
        ),
        tags=["Academic Ontology"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete a lesson record instead of issuing a SQL DELETE.

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
