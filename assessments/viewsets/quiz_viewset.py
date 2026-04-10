from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from assessments.models import Quiz
from assessments.serializers import QuizDetailSerializer, QuizListSerializer


class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoints for browsing active quizzes and their questions.
    List returns a compact summary; detail returns the full question set
    with answer choices for the Angular quiz-taking UI.

    **Public endpoint -- no authentication required.**
    """

    queryset = Quiz.objects.filter(is_active=True)
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return QuizDetailSerializer
        return QuizListSerializer

    @swagger_auto_schema(
        operation_summary="List active quizzes",
        operation_description="Returns a paginated list of all active quizzes.",
        tags=["Assessments"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve quiz with questions and choices",
        operation_description=(
            "Returns the full quiz detail including all questions and their "
            "answer choices. Used by the Angular quiz-taking UI to render the exam."
        ),
        tags=["Assessments"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
