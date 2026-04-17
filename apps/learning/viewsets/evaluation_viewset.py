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
        """Processes the serialized evaluation and triggers the autonomous deterministic Go computation array pipeline.

        Args:
            request (Request): The incoming authenticated HTTP REST framework request pipeline sequence.
            *args: Variable length parameter list bindings.
            **kwargs: Arbitrary dictionary keyword arguments mapping.

        Returns:
            Response: A structured DRF Response instance binding the sequential AxiomEngine adaptive plan output JSON payload map.
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
        """Produces a paginated sequential relational array listing corresponding to all available evaluation topological records.

        Args:
            request (Request): The incoming authenticated sequence REST request component.
            *args: Variable length argument map index parameters.
            **kwargs: Arbitrary parameter mapping keyword configurations.

        Returns:
            Response: A formatted paginated serialized model dict instance mapped response array.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Evaluations"])
    def retrieve(self, request, *args, **kwargs):
        """Retrieves and sequentially parses a singular discrete relational mapping record designated by the provided primary key identifier.

        Args:
            request (Request): The incoming standard application REST topological request configuration.
            *args: Variable length operational parameter sequences.
            **kwargs: Arbitrary contextual map arguments mapping.

        Returns:
            Response: A unified structured serialization configuration derived from the absolute corresponding Evaluation object parameter array.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Evaluations"])
    def update(self, request, *args, **kwargs):
        """Applies a complete structural HTTP PUT topological sequence to a referenced Evaluation instance pointer.

        Args:
            request (Request): The inbound structured DRF REST framework mapped sequence array payload.
            *args: Operational variable parameter topological list structures.
            **kwargs: Dynamic relational dictionary operational arguments mappings.

        Returns:
            Response: An isolated DRF Response detailing the fully modified JSON instance topological struct format.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Evaluations"])
    def partial_update(self, request, *args, **kwargs):
        """Parses and sequentially incorporates a partial HTTP PATCH update parameter sequence constraint to the objective Evaluation dictionary mapping instance.

        Args:
            request (Request): The inbound HTTP framework topological segment map.
            *args: Contextual numeric and logical array parameter list pointers.
            **kwargs: Distinct relational structure key-to-value map structures.

        Returns:
            Response: A detailed array containing the specifically modified parameter structures mapping configuration layout.
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
