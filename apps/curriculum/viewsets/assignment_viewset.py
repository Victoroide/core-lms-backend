from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.curriculum.models import Assignment
from apps.curriculum.serializers import AssignmentSerializer
from apps.learning.permissions import IsTutor


class AssignmentViewSet(viewsets.ModelViewSet):
    """CRUD for Lesson Assignment entities.

    Read operations are available to any authenticated user.
    Create, update, and delete are restricted to tutors.

    **Requires authentication.**
    """

    queryset = Assignment.objects.select_related(
        "lesson__module__course", "created_by"
    ).all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["lesson", "created_by", "is_deleted"]

    def get_permissions(self):
        """Restrict mutation operations to tutors.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List assignments",
        operation_description=(
            "Returns a paginated list of lesson assignments. Filter by ?lesson=<id>."
        ),
        tags=["Assignments"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of assignment records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized assignment data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve an assignment",
        operation_description="Returns a single assignment by ID.",
        tags=["Assignments"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single assignment record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized assignment data.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create an assignment",
        operation_description="Creates a new lesson assignment. Restricted to tutors.",
        tags=["Assignments"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new assignment record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized assignment data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update an assignment",
        operation_description="Full update of an assignment. Restricted to tutors.",
        tags=["Assignments"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to an assignment record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated assignment data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update an assignment",
        operation_description="Partial update of an assignment. Restricted to tutors.",
        tags=["Assignments"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to an assignment record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated assignment data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete an assignment",
        operation_description=(
            "Soft-deletes an assignment (marks is_deleted=True). Restricted to tutors."
        ),
        tags=["Assignments"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete an assignment record instead of issuing a SQL DELETE.

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
