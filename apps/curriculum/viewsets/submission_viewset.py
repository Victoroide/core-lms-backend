from decimal import Decimal, InvalidOperation

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.curriculum.models import Submission
from apps.curriculum.serializers import SubmissionSerializer
from apps.learning.permissions import IsStudent, IsTutor


class SubmissionViewSet(viewsets.ModelViewSet):
    """CRUD for student file submissions on Lesson Assignments.

    Row-level isolation is enforced: students can only see their
    own submissions; tutors can see all submissions.

    Students can create submissions. Tutors can grade them via
    the PATCH /submissions/{id}/grade/ action.

    **Requires authentication.**
    """

    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["assignment", "is_deleted"]

    def get_queryset(self):
        """Scope submissions to the requesting user's role.

        Students receive only their own submissions.
        Tutors receive all submissions.

        Returns:
            QuerySet: Filtered submission queryset.
        """
        user = self.request.user
        if getattr(user, "role", None) == "STUDENT":
            return Submission.objects.filter(
                student=user
            ).select_related("assignment__lesson", "student")
        return Submission.objects.select_related(
            "assignment__lesson", "student"
        ).all()

    def get_permissions(self):
        """Students can create; tutors can grade; both can read.

        Returns:
            list: Permission instances for the current action.
        """
        if self.action == "create":
            return [IsStudent()]
        if self.action in ("update", "partial_update", "destroy"):
            return [IsTutor()]
        if self.action == "grade":
            return [IsTutor()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List submissions",
        operation_description=(
            "Returns submissions scoped by role. Students see only their own; "
            "tutors see all. Filter by ?assignment=<id>."
        ),
        tags=["Submissions"],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of submission records.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Paginated serialized submission data.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a submission",
        operation_description="Returns a single submission by ID (respects row-level isolation).",
        tags=["Submissions"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Return a single submission record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized submission data.
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Submit an assignment",
        operation_description="Upload a file submission for an assignment. Restricted to students.",
        tags=["Submissions"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new submission record with file upload.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized submission data with HTTP 201 status.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Grade a student submission",
        operation_description="Apply a numeric grade to a submitted assignment. Restricted to tutors.",
        tags=["Submissions"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["grade"],
            properties={
                "grade": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Numeric grade to assign.",
                ),
            },
        ),
        responses={
            200: "Submission graded successfully.",
            400: "Invalid grade value.",
        },
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsTutor])
    def grade(self, request, pk=None):
        """Apply a numeric grade to a submitted assignment.

        Args:
            request (Request): The incoming authenticated HTTP request containing grade data.
            pk (int, optional): Primary key of the submission to grade.

        Returns:
            Response: Serialized submission data with updated grade.
        """
        submission = self.get_object()
        grade_value = request.data.get("grade")

        if grade_value is None:
            return Response(
                {"error": "grade is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            grade_decimal = Decimal(str(grade_value))
        except (InvalidOperation, ValueError):
            return Response(
                {"error": "Invalid grade value."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone

        submission.grade = grade_decimal
        submission.graded_at = timezone.now()
        submission.save(update_fields=["grade", "graded_at"])

        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update a submission",
        operation_description="Full update of a submission record. Restricted to tutors.",
        tags=["Submissions"],
    )
    def update(self, request, *args, **kwargs):
        """Apply a full update to a submission record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated submission data.
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partial update a submission",
        operation_description="Partial update of a submission record. Restricted to tutors.",
        tags=["Submissions"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Apply a partial update to a submission record.

        Args:
            request (Request): The incoming authenticated HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Serialized updated submission data.
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft-delete a submission",
        operation_description="Soft-deletes a submission (marks is_deleted=True). Restricted to tutors.",
        tags=["Submissions"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft-delete a submission record instead of issuing a SQL DELETE.

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
