from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning.models import Career
from apps.learning.permissions import IsTutor
from apps.learning.serializers import CareerSerializer, CareerDetailSerializer


class CareerViewSet(viewsets.ModelViewSet):
    """CRUD for Career (degree program) entities.

    List and retrieve are available to any authenticated user.
    Create, update, and delete are restricted to tutors.

    **Requires authentication.**
    """

    queryset = Career.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_deleted"]

    def get_serializer_class(self):
        """Return the appropriate serializer based on the action.

        Returns:
            type: CareerDetailSerializer for retrieve, CareerSerializer otherwise.
        """
        if self.action == "retrieve":
            return CareerDetailSerializer
        return CareerSerializer

    def get_permissions(self):
        """Restrict mutation operations to tutors.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List all careers",
        operation_description="Returns a paginated list of all degree programs.",
        tags=["Academic Ontology"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of all career records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized career data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a career with nested semesters",
        operation_description="Returns a single career with its semesters nested in the response.",
        tags=["Academic Ontology"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single career with nested semester data.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized career data with nested semesters.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new career",
        operation_description="Creates a new degree program. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new career record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized career data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a career",
        operation_description="Full update of a career record. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a career record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated career data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update a career",
        operation_description="Partial update of a career record. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a career record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated career data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete a career",
        operation_description="Soft-deletes a career (marks is_deleted=True). Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete a career record instead of issuing a SQL DELETE.

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
