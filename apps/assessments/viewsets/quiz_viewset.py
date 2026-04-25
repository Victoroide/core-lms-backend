from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.assessments.models import Quiz
from apps.assessments.serializers import (
    QuizDetailSerializer,
    QuizListSerializer,
    QuizTutorSerializer,
)
from apps.learning.permissions import IsTutor


class QuizViewSet(viewsets.ModelViewSet):
    """Endpoints for browsing and managing quizzes.
    Tutors can create, update, and delete quizzes. Students can only read active quizzes.
    """

    def get_queryset(self):
        queryset = Quiz.objects.all()
        is_tutor = (
            self.request.user.is_authenticated
            and self.request.user.role == "TUTOR"
        )
        if not is_tutor:
            queryset = queryset.filter(is_active=True)

        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsTutor()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == "list":
            return QuizListSerializer
        if self.request.user.is_authenticated and self.request.user.role == "TUTOR":
            return QuizTutorSerializer
        return QuizDetailSerializer

    @swagger_auto_schema(
        operation_summary="List active quizzes",
        operation_description="Returns a paginated list of all active quizzes.",
        tags=["Quizzes"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of active quizzes.

        Args:
            request (Request): The incoming HTTP request.

        Returns:
            Response: A DRF Response containing the serialized quiz list.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve quiz with questions and choices",
        operation_description=(
            "Returns the full quiz detail including all questions and their "
            "answer choices. Used by the Angular quiz-taking UI to render the exam."
        ),
        tags=["Quizzes"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single quiz with nested questions and answer choices.

        Args:
            request (Request): The incoming HTTP request.

        Returns:
            Response: A DRF Response with the serialized quiz detail payload.
        """
        return super().retrieve(request, *args, **kwargs)
