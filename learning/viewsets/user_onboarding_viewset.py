from collections import defaultdict

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from learning.models import LMSUser


class VARKAnswerSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=["visual", "aural", "read_write", "kinesthetic"]
    )
    value = serializers.IntegerField(min_value=0, max_value=10)


class VARKOnboardingSerializer(serializers.Serializer):
    answers = VARKAnswerSerializer(many=True)


# ---------------------------------------------------------------------------
# Swagger schema definitions
# ---------------------------------------------------------------------------

_vark_answer_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["category", "value"],
    properties={
        "category": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["visual", "aural", "read_write", "kinesthetic"],
            description="VARK learning modality category.",
            example="visual",
        ),
        "value": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            minimum=0,
            maximum=10,
            description="Score for this modality (0-10).",
            example=7,
        ),
    },
)

_onboard_body_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["answers"],
    properties={
        "answers": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=_vark_answer_schema,
            description="Array of VARK questionnaire responses.",
        ),
    },
)

_onboard_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "student_id": openapi.Schema(
            type=openapi.TYPE_INTEGER, example=2,
        ),
        "vark_scores": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            additional_properties=openapi.Schema(type=openapi.TYPE_INTEGER),
            example={"visual": 7, "aural": 3, "read_write": 5, "kinesthetic": 4},
        ),
        "vark_dominant": openapi.Schema(
            type=openapi.TYPE_STRING,
            example="visual",
        ),
    },
)

_onboard_error_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(type=openapi.TYPE_STRING, example="validation_error"),
        "details": openapi.Schema(type=openapi.TYPE_STRING, example="No answers provided."),
    },
)


class UserViewSet(viewsets.GenericViewSet):
    """Handles user-scoped operations that do not fit into standard CRUD.
    Currently exposes the VARK onboarding action.

    **Requires authentication.**
    """

    queryset = LMSUser.objects.all()
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="VARK onboarding questionnaire",
        operation_description=(
            "Submit the VARK questionnaire results for a student. "
            "Computes the dominant learning modality from the provided "
            "scores and persists it to the user profile."
        ),
        tags=["Learning"],
        request_body=_onboard_body_schema,
        responses={
            200: openapi.Response(
                description="VARK profile computed and saved.",
                schema=_onboard_response_schema,
            ),
            400: openapi.Response(
                description="Validation error.",
                schema=_onboard_error_schema,
            ),
        },
    )
    @action(detail=True, methods=["post"], url_path="onboard")
    def onboard(self, request, pk=None):
        """Calculates and dynamically persists the overriding VARK modality index context.

        Args:
            request (Request): The incoming authenticated HTTP REST framework request payload configuration segment.
            pk (int, optional): The unified parameter string pointer referencing the targeted schema. Defaults to None.

        Returns:
            Response: A valid JSON layout referencing the dynamically updated string constant map keys or integral failure mapping properties.
        """
        user = self.get_object()

        serializer = VARKOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        scores = defaultdict(int)
        for answer in serializer.validated_data["answers"]:
            scores[answer["category"]] += answer["value"]

        if not scores:
            return Response(
                {"error": "validation_error", "details": "No answers provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dominant = max(scores, key=scores.get)
        user.vark_dominant = dominant
        user.save(update_fields=["vark_dominant"])

        return Response(
            {
                "student_id": user.pk,
                "vark_scores": dict(scores),
                "vark_dominant": dominant,
            },
            status=status.HTTP_200_OK,
        )
