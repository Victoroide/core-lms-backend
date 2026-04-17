"""ViewSet for EvaluationTelemetry CRUD operations."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assessments.serializers.telemetry_serializer import (
    EvaluationTelemetrySerializer,
)
from apps.learning.models import EvaluationTelemetry
from apps.learning.permissions import IsStudent, IsTutor


class EvaluationTelemetryViewSet(viewsets.ModelViewSet):
    """CRUD for EvaluationTelemetry records.

    Students can create telemetry records for their own evaluations.
    Tutors can list and retrieve all telemetry records.
    Students can only see telemetry for their own evaluations.

    **Requires authentication.**
    """

    serializer_class = EvaluationTelemetrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Scope telemetry records by the requesting user's role.

        Students see only telemetry for their own evaluations.
        Tutors see all telemetry records.

        Returns:
            QuerySet: Filtered telemetry queryset.
        """
        user = self.request.user
        if getattr(user, "role", None) == "STUDENT":
            return EvaluationTelemetry.objects.filter(
                evaluation__student=user
            ).select_related("evaluation")
        return EvaluationTelemetry.objects.select_related("evaluation").all()

    def get_permissions(self):
        """Students can create; tutors can read all; both can read own.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action == "create":
            return [IsStudent()]
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsTutor()]

    @swagger_auto_schema(
        operation_summary="Create evaluation telemetry",
        operation_description=(
            "Record behavioral telemetry for an evaluation session. "
            "Restricted to students."
        ),
        tags=["Proctoring"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["evaluation", "time_on_task_seconds", "clicks"],
            properties={
                "evaluation": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Primary key of the Evaluation.",
                ),
                "time_on_task_seconds": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Total time on task in seconds.",
                ),
                "clicks": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Total click count during the session.",
                ),
            },
        ),
        responses={
            201: EvaluationTelemetrySerializer,
            400: "Validation error.",
        },
    )
    def create(self, request, *args, **kwargs):
        """Create a new evaluation telemetry record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized telemetry data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="List evaluation telemetry",
        operation_description=(
            "Returns a paginated list of evaluation telemetry records. "
            "Students see only their own; tutors see all."
        ),
        tags=["Proctoring"],
        responses={200: EvaluationTelemetrySerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of telemetry records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized telemetry data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve evaluation telemetry",
        operation_description="Returns a single telemetry record by ID.",
        tags=["Proctoring"],
        responses={200: EvaluationTelemetrySerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single telemetry record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized telemetry data.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update evaluation telemetry",
        operation_description="Full update of a telemetry record. Restricted to tutors.",
        tags=["Proctoring"],
        responses={200: EvaluationTelemetrySerializer},
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a telemetry record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated telemetry data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update evaluation telemetry",
        operation_description="Partial update of a telemetry record. Restricted to tutors.",
        tags=["Proctoring"],
        responses={200: EvaluationTelemetrySerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a telemetry record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated telemetry data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete evaluation telemetry",
        operation_description="Delete a telemetry record. Restricted to tutors.",
        tags=["Proctoring"],
        responses={204: "Telemetry deleted."},
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a telemetry record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: HTTP 204 No Content.
        """
        return super().destroy(request, *args, **kwargs)
