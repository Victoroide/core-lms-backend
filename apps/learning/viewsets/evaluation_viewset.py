import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning.models import Evaluation
from apps.learning.serializers import EvaluationSerializer
from apps.learning.services import AxiomEngineClient, AxiomEngineError, AxiomEngineTimeout

logger = logging.getLogger(__name__)


class EvaluationViewSet(viewsets.ModelViewSet):
    """CRUD for evaluations. On create, the evaluation is persisted to
    PostgreSQL and then synchronously forwarded to the AxiomEngine Go
    microservice. The adaptive study plan returned by AxiomEngine is
    injected into the 201 response body alongside the evaluation data.

    **Requires authentication.**
    """

    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create an evaluation and trigger AxiomEngine",
        operation_description=(
            "Persists a new evaluation record. If the evaluation contains "
            "failed topics, it synchronously requests an adaptive study plan "
            "from the AxiomEngine Go microservice. The adaptive plan (or any "
            "AxiomEngine error) is returned alongside the evaluation data."
        ),
        tags=["Evaluations"],
        responses={
            201: "Evaluation created. Includes adaptive_plan if applicable.",
            400: "Validation error.",
        },
    )
    def create(self, request, *args, **kwargs):
        """Persist a new evaluation and request an adaptive plan from AxiomEngine.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: A DRF Response with the evaluation data plus the
                AxiomEngine adaptive plan (or an ``axiom_error`` mapping).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluation = serializer.save()

        adaptive_plan = None
        axiom_error = None

        if evaluation.failed_topics.exists():
            try:
                client = AxiomEngineClient()
                adaptive_plan = client.request_adaptive_plan(evaluation.pk)
            except AxiomEngineTimeout as exc:
                logger.warning("AxiomEngine timeout for eval %d: %s", evaluation.pk, exc)
                axiom_error = {"error": "axiom_timeout", "details": str(exc)}
            except AxiomEngineError as exc:
                logger.warning("AxiomEngine error for eval %d: %s", evaluation.pk, exc)
                axiom_error = {
                    "error": "axiom_error",
                    "status_code": exc.status_code,
                    "details": exc.detail,
                }

        response_data = serializer.data
        response_data["adaptive_plan"] = adaptive_plan
        if axiom_error:
            response_data["axiom_error"] = axiom_error

        return Response(response_data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["Evaluations"])
    def list(self, request, *args, **kwargs):
        """Return a paginated list of evaluations.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized evaluation data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Evaluations"])
    def retrieve(self, request, *args, **kwargs):
        """Return a single evaluation identified by primary key.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized evaluation data.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Evaluations"])
    def update(self, request, *args, **kwargs):
        """Apply a full update to an evaluation record (HTTP PUT).

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated evaluation data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Evaluations"])
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to an evaluation record (HTTP PATCH).

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated evaluation data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Evaluations"])
    def destroy(self, request, *args, **kwargs):
        """Delete an evaluation record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: HTTP 204 No Content.
        """
        return super().destroy(request, *args, **kwargs)
