from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning.models import Semester
from apps.learning.permissions import IsTutor
from apps.learning.serializers import SemesterSerializer


class SemesterViewSet(viewsets.ModelViewSet):
    """CRUD for Semester entities.

    Supports filtering by career via the ?career query parameter.
    List and retrieve are available to any authenticated user.
    Create, update, and delete are restricted to tutors.

    **Requires authentication.**
    """

    queryset = Semester.objects.select_related("career").all()
    serializer_class = SemesterSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["career", "is_deleted"]

    def get_permissions(self):
        """Restrict mutation operations to tutors.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List semesters",
        operation_description="Returns a paginated list of semesters. Filter by ?career=<id>.",
        tags=["Academic Ontology"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of semester records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized semester data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a semester",
        operation_description="Returns a single semester by ID.",
        tags=["Academic Ontology"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single semester record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized semester data.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a semester",
        operation_description="Creates a new semester within a career. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new semester record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized semester data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a semester",
        operation_description="Full update of a semester. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a semester record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated semester data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update a semester",
        operation_description="Partial update of a semester. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a semester record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated semester data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete a semester",
        operation_description=(
            "Soft-deletes a semester (marks is_deleted=True). Restricted to tutors."
        ),
        tags=["Academic Ontology"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete a semester record instead of issuing a SQL DELETE.

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
