import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.models import AttemptAnswer, Quiz, QuizAttempt
from assessments.serializers import AttemptResultSerializer, AttemptSubmitSerializer
from assessments.services import ScoringService
from learning.models import LMSUser
from learning.permissions import IsStudent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Swagger schema definitions
# ---------------------------------------------------------------------------

_answer_item_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["question_id", "selected_choice_id"],
    properties={
        "question_id": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="Primary key of the Question being answered.",
            example=1,
        ),
        "selected_choice_id": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="Primary key of the AnswerChoice the student selected.",
            example=3,
        ),
    },
)

_submit_body_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["quiz_id", "student_id", "answers"],
    properties={
        "quiz_id": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="Primary key of the Quiz being attempted.",
            example=1,
        ),
        "student_id": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="Primary key of the authenticated student.",
            example=2,
        ),
        "answers": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=_answer_item_schema,
            description="Array of question-to-choice mappings.",
        ),
    },
)

_attempt_result_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        "student": openapi.Schema(type=openapi.TYPE_INTEGER, example=2),
        "quiz": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        "start_time": openapi.Schema(
            type=openapi.TYPE_STRING, format="date-time",
        ),
        "end_time": openapi.Schema(
            type=openapi.TYPE_STRING, format="date-time", nullable=True,
        ),
        "final_score": openapi.Schema(
            type=openapi.TYPE_NUMBER, format="decimal", example=80.00,
        ),
        "is_submitted": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
        "evaluation_id": openapi.Schema(
            type=openapi.TYPE_INTEGER, example=1, nullable=True,
        ),
        "failed_topics": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            example=["Objects", "Polymorphism"],
        ),
        "adaptive_plan": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Adaptive study plan returned by AxiomEngine (nullable).",
            nullable=True,
        ),
    },
)

_validation_error_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(type=openapi.TYPE_STRING, example="validation_error"),
        "details": openapi.Schema(type=openapi.TYPE_STRING, example="Student not found."),
    },
)


class AttemptViewSet(viewsets.ViewSet):
    """Handles quiz submission. When the Angular frontend POSTs a completed
    quiz, this viewset:
      1. Creates the QuizAttempt and AttemptAnswer records.
      2. Delegates to ScoringService to compute the score, create Evaluation
         and FailedTopic records, and trigger AxiomEngine.
      3. Returns the scoring result with the adaptive plan (or error).

    **Requires authentication and STUDENT role.**
    """

    permission_classes = [IsAuthenticated, IsStudent]

    @swagger_auto_schema(
        operation_summary="Submit a quiz attempt",
        operation_description=(
            "Submit the student's answers for a quiz. The backend will:\n"
            "1. Create a QuizAttempt and AttemptAnswer records.\n"
            "2. Score the attempt and generate an Evaluation.\n"
            "3. Forward failed topics to AxiomEngine for an adaptive study plan.\n"
            "4. Return the complete result including the adaptive plan."
        ),
        tags=["Assessments"],
        request_body=_submit_body_schema,
        responses={
            201: openapi.Response(
                description="Quiz scored successfully. Includes adaptive study plan.",
                schema=_attempt_result_schema,
            ),
            400: openapi.Response(
                description="Validation error (invalid student, quiz, or payload).",
                schema=_validation_error_schema,
            ),
        },
    )
    def create(self, request):
        """Processes the inbound authenticated evaluation component sequence.

        Args:
            request (Request): The incoming authenticated HTTP REST framework request pipeline segment with JSON operational payload.

        Returns:
            Response: A structured DRF Response object containing the serialized AttemptResult mapping arrays and contextual response codes.
        """
        serializer = AttemptSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            student = LMSUser.objects.get(pk=data["student_id"])
            quiz = Quiz.objects.get(pk=data["quiz_id"])
        except LMSUser.DoesNotExist:
            return Response(
                {"error": "validation_error", "details": "Student not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Quiz.DoesNotExist:
            return Response(
                {"error": "validation_error", "details": "Quiz not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attempt = QuizAttempt.objects.create(student=student, quiz=quiz)

        answer_objects = []
        for ans in data["answers"]:
            answer_objects.append(
                AttemptAnswer(
                    attempt=attempt,
                    question_id=ans["question_id"],
                    selected_choice_id=ans["selected_choice_id"],
                )
            )
        AttemptAnswer.objects.bulk_create(answer_objects)

        scoring_service = ScoringService()
        result = scoring_service.score_and_evaluate(attempt)

        attempt.refresh_from_db()
        attempt_data = AttemptResultSerializer(attempt).data
        attempt_data.update(result)

        return Response(attempt_data, status=status.HTTP_201_CREATED)
