from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from apps.learning.models import Certificate, Course, LMSUser
from apps.learning.permissions import IsStudent
from apps.learning.services import CertificateGenerator, CertificateEligibilityError


class CertificateViewSet(viewsets.ViewSet):
    """Handles certificate generation for students who have completed a course.

    Provides a POST action to issue a verifiable SHA-256 certificate
    after validating that the student meets passing requirements.

    **Requires authentication and STUDENT role.**
    """

    def get_permissions(self):
        """Allow public access for verification, require student role for generation."""
        if self.action == "verify":
            return [AllowAny()]
        return [IsAuthenticated(), IsStudent()]

    @swagger_auto_schema(
        operation_summary="Generate a course-completion certificate",
        operation_description=(
            "Issue a verifiable certificate for a student who has passed a course. "
            "Returns the certificate hash, issued_at timestamp, and related IDs. "
            "Idempotent: if a certificate already exists, it is returned."
        ),
        tags=["Certificates"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["student_id", "course_id"],
            properties={
                "student_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Primary key of the student.",
                    example=2,
                ),
                "course_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Primary key of the course.",
                    example=1,
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Certificate issued successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "certificate_hash": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="a3f8c2e1b4d6...",
                        ),
                        "issued_at": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format="date-time",
                        ),
                        "course_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=1,
                        ),
                        "student_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=2,
                        ),
                    },
                ),
            ),
            400: "Validation error or student/course not found.",
            403: "Student has not met passing requirements.",
        },
    )
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """Issue a course-completion certificate for the specified student.

        Args:
            request (Request): Must contain student_id and course_id in the body.

        Returns:
            Response: Certificate data with HTTP 201, or error details.
        """
        student_id = request.data.get("student_id")
        course_id = request.data.get("course_id")

        if not student_id or not course_id:
            return Response(
                {"error": "student_id and course_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            student = LMSUser.objects.get(pk=student_id)
        except LMSUser.DoesNotExist:
            return Response(
                {"error": "Student not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generator = CertificateGenerator()
            certificate = generator.issue_certificate(student, course)
        except CertificateEligibilityError as exc:
            return Response(
                {"error": "ineligible", "detail": exc.reason},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "certificate_hash": certificate.certificate_hash,
                "issued_at": certificate.issued_at.isoformat(),
                "course_id": certificate.course_id,
                "student_id": certificate.student_id,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="Verify a course-completion certificate",
        operation_description=(
            "Publicly verifiable endpoint. Returns certificate metadata "
            "if the provided SHA-256 hash exists in the system."
        ),
        tags=["Certificates"],
        responses={
            200: openapi.Response(
                description="Certificate found and verified.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "is_valid": openapi.Schema(
                            type=openapi.TYPE_BOOLEAN, example=True
                        ),
                        "hash": openapi.Schema(
                            type=openapi.TYPE_STRING, example="a3f8..."
                        ),
                        "issued_at": openapi.Schema(
                            type=openapi.TYPE_STRING, format="date-time"
                        ),
                        "student_name": openapi.Schema(
                            type=openapi.TYPE_STRING, example="John Doe"
                        ),
                        "course_name": openapi.Schema(
                            type=openapi.TYPE_STRING, example="Advanced Programming"
                        ),
                    },
                ),
            ),
            404: "Certificate not found.",
        },
    )
    @action(detail=False, methods=["get"], url_path=r"verify/(?P<hash>[a-f0-9]+)")
    def verify(self, request, hash=None):
        """Publicly verify a certificate hash and retrieve its metadata.

        Args:
            request (Request): The request object.
            hash (str): The SHA-256 certificate hash from the URL.

        Returns:
            Response: Certificate metadata with HTTP 200, or 404 if invalid.
        """
        try:
            certificate = Certificate.objects.select_related("student", "course").get(
                certificate_hash=hash
            )
        except Certificate.DoesNotExist:
            return Response(
                {"error": "Invalid or non-existent certificate hash."},
                status=status.HTTP_404_NOT_FOUND,
            )

        student_name = f"{certificate.student.first_name} {certificate.student.last_name}".strip()
        if not student_name:
            student_name = certificate.student.username

        return Response(
            {
                "is_valid": True,
                "hash": certificate.certificate_hash,
                "issued_at": certificate.issued_at.isoformat(),
                "student_name": student_name,
                "course_name": certificate.course.name,
            },
            status=status.HTTP_200_OK,
        )
