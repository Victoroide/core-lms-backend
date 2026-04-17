from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning.models import Module
from apps.learning.permissions import IsTutor
from apps.learning.serializers import ModuleSerializer


class ModuleViewSet(viewsets.ModelViewSet):
    """CRUD for Module entities (thematic sections within a Course).

    Supports filtering by course via the ?course query parameter.
    List and retrieve are available to any authenticated user.
    Create, update, and delete are restricted to tutors.

    **Requires authentication.**
    """

    queryset = Module.objects.select_related("course").all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["course", "is_deleted"]

    def get_permissions(self):
        """Restrict mutation operations to tutors.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List modules",
        operation_description="Returns a paginated list of modules. Filter by ?course=<id>.",
        tags=["Academic Ontology"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of module records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized module data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a module",
        operation_description="Returns a single module by ID.",
        tags=["Academic Ontology"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single module record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized module data.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a module",
        operation_description="Creates a new module within a course. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new module record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized module data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a module",
        operation_description="Full update of a module. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a module record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated module data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update a module",
        operation_description="Partial update of a module. Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a module record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated module data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete a module",
        operation_description="Soft-deletes a module (marks is_deleted=True). Restricted to tutors.",
        tags=["Academic Ontology"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete a module record instead of issuing a SQL DELETE.

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
