import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.models import ProctoringLog
from assessments.serializers import ProctoringBulkSerializer
from learning.permissions import IsStudent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Swagger schema definitions
# ---------------------------------------------------------------------------

_proctoring_event_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["attempt", "event_type", "timestamp", "severity_score"],
    properties={
        "attempt": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="Primary key of the QuizAttempt this event belongs to.",
            example=1,
        ),
        "event_type": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["tab_switched", "face_not_detected", "multiple_faces"],
            description="Type of anti-cheat event detected.",
            example="tab_switched",
        ),
        "timestamp": openapi.Schema(
            type=openapi.TYPE_STRING,
            format="date-time",
            description="ISO-8601 UTC timestamp of the event.",
            example="2026-04-09T22:15:30Z",
        ),
        "severity_score": openapi.Schema(
            type=openapi.TYPE_NUMBER,
            format="decimal",
            description="Severity weight (0.00 - 9.99).",
            example=0.85,
        ),
    },
)

_proctoring_body_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["events"],
    properties={
        "events": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=_proctoring_event_schema,
            description="Batched array of proctoring telemetry events.",
        ),
    },
)

_proctoring_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "ingested": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="Number of events successfully persisted.",
            example=5,
        ),
    },
)


class ProctoringViewSet(viewsets.ViewSet):
    """High-throughput endpoint for ingesting proctoring telemetry from the
    frontend face-api.js and tab-visibility monitors. Accepts batched arrays
    of events and persists them via bulk_create.

    **Requires authentication and STUDENT role.**
    """

    permission_classes = [IsAuthenticated, IsStudent]

    @swagger_auto_schema(
        operation_summary="Ingest proctoring telemetry events",
        operation_description=(
            "Accepts a batched array of anti-cheat events captured by the "
            "frontend proctoring system (face-api.js, tab-visibility API). "
            "Events are persisted via bulk_create for post-hoc integrity analysis."
        ),
        tags=["Assessments"],
        request_body=_proctoring_body_schema,
        responses={
            201: openapi.Response(
                description="Events ingested successfully.",
                schema=_proctoring_response_schema,
            ),
            400: "Validation error in event payload.",
        },
    )
    def create(self, request):
        """Asynchronously parses and ingests batched relational anti-cheat telemetry event schemas.

        Args:
            request (Request): The incoming authenticated HTTP REST framework request pipeline component.

        Returns:
            Response: A structured DRF Response metric detailing the integral count of structural events committed.
        """
        serializer = ProctoringBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        events_data = serializer.validated_data["events"]
        logs = [ProctoringLog(**event) for event in events_data]
        created = ProctoringLog.objects.bulk_create(logs)

        logger.info("Proctoring: ingested %d events", len(created))

        return Response(
            {"ingested": len(created)},
            status=status.HTTP_201_CREATED,
        )
