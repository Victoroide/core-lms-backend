from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning.models import Resource
from apps.learning.permissions import IsTutor
from apps.learning.serializers import ResourceSerializer


class ResourceViewSet(viewsets.ModelViewSet):
    """CRUD for Resource entities (file attachments on Lessons).

    Read operations are available to any authenticated user.
    Create, update, and delete are restricted to tutors.

    Files are stored in S3 under the path resources/{course_id}/{filename}.

    **Requires authentication.**
    """

    queryset = Resource.objects.select_related(
        "lesson__module__course", "uploaded_by"
    ).all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["lesson", "resource_type", "is_deleted"]

    def get_permissions(self):
        """Restrict mutation operations to tutors.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List resources",
        operation_description="Returns a paginated list of resources. Filter by ?lesson=<id> or ?resource_type=<type>.",
        tags=["Resources"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of resource records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized resource data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a resource",
        operation_description="Returns a single resource by ID including the S3 file URL.",
        tags=["Resources"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single resource record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized resource data.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Upload a resource",
        operation_description="Upload a new file resource to a lesson. Restricted to tutors.",
        tags=["Resources"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new resource record with file upload.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized resource data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a resource",
        operation_description="Full update of a resource record. Restricted to tutors.",
        tags=["Resources"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a resource record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated resource data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update a resource",
        operation_description="Partial update of a resource record. Restricted to tutors.",
        tags=["Resources"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a resource record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated resource data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete a resource",
        operation_description="Soft-deletes a resource (marks is_deleted=True). Restricted to tutors.",
        tags=["Resources"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete a resource record instead of issuing a SQL DELETE.

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
