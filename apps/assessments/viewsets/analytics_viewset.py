from django.db.models import Avg, Count
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assessments.models import ProctoringLog, QuizAttempt
from apps.learning.models import Course, Evaluation, FailedTopic, LMSUser
from apps.learning.permissions import IsTutor

# ---------------------------------------------------------------------------
# Response schema definitions for Swagger documentation
# ---------------------------------------------------------------------------

_failed_concept_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "concept_id": openapi.Schema(
            type=openapi.TYPE_STRING,
            example="Polymorphism",
        ),
        "fail_count": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            example=3,
        ),
    },
)

_dashboard_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "course_id": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            example=1,
        ),
        "course_code": openapi.Schema(
            type=openapi.TYPE_STRING,
            example="CS-201",
        ),
        "course_name": openapi.Schema(
            type=openapi.TYPE_STRING,
            example="Advanced Programming",
        ),
        "total_enrolled_students": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            example=10,
        ),
        "average_quiz_score": openapi.Schema(
            type=openapi.TYPE_NUMBER,
            format="float",
            example=72.50,
        ),
        "proctoring_alerts": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            additional_properties=openapi.Schema(type=openapi.TYPE_INTEGER),
            example={"tab_switched": 6, "multiple_faces": 4},
        ),
        "vark_distribution": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            additional_properties=openapi.Schema(type=openapi.TYPE_INTEGER),
            example={
                "visual": 3,
                "aural": 2,
                "read_write": 3,
                "kinesthetic": 2,
            },
        ),
        "top_failed_concepts": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=_failed_concept_schema,
        ),
    },
)

_error_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(type=openapi.TYPE_STRING, example="not_found"),
        "detail": openapi.Schema(type=openapi.TYPE_STRING, example="Course not found."),
    },
)


class TeacherDashboardViewSet(viewsets.ViewSet):
    """Read-only analytics endpoint for the Teacher (Mentor) Dashboard.

    Provides per-course aggregate statistics including enrollment counts,
    average quiz scores, proctoring alert summaries, VARK distribution,
    and the most-failed concepts for targeted review.

    **Requires authentication and TUTOR role.**
    """

    permission_classes = [IsAuthenticated, IsTutor]

    CRITICAL_EVENT_TYPES = [
        ProctoringLog.EventType.TAB_SWITCHED,
        ProctoringLog.EventType.MULTIPLE_FACES,
    ]

    @swagger_auto_schema(
        operation_summary="Course analytics dashboard",
        operation_description=(
            "Returns aggregated metrics for a specific course: enrollment count, "
            "average quiz score, critical proctoring alerts, VARK distribution of "
            "enrolled students, and the top 3 most-failed concept IDs."
        ),
        tags=["Analytics"],
        manual_parameters=[
            openapi.Parameter(
                "course_id",
                openapi.IN_PATH,
                description="Primary key of the course to analyze.",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Dashboard metrics computed successfully.",
                schema=_dashboard_response_schema,
            ),
            404: openapi.Response(
                description="Course not found.",
                schema=_error_schema,
            ),
        },
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"course/(?P<course_id>[^/.]+)/dashboard",
    )
    def course_dashboard(self, request, course_id=None):
        """Processes and dynamically computes the core dashboard metric structures for a targeted course context.

        Args:
            request (Request): The incoming authenticated HTTP REST framework request pipeline segment.
            course_id (int, optional): The universally unique identifier string for the objective course context mapping. Defaults to None.

        Returns:
            Response: A structured DRF Response object containing the serialized JSON topological metadata mapping arrays.
        """
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response(
                {"error": "not_found", "detail": "Course not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # -- Total Enrolled Students ------------------------------------------
        eval_student_ids = set(
            Evaluation.objects.filter(course=course)
            .values_list("student_id", flat=True)
        )
        attempt_student_ids = set(
            QuizAttempt.objects.filter(quiz__course=course)
            .values_list("student_id", flat=True)
        )
        enrolled_student_ids = eval_student_ids | attempt_student_ids
        total_enrolled_students = len(enrolled_student_ids)

        # -- Average Quiz Score ------------------------------------------------
        agg = QuizAttempt.objects.filter(
            quiz__course=course,
            is_submitted=True,
            final_score__isnull=False,
        ).aggregate(avg_score=Avg("final_score"))
        average_quiz_score = round(float(agg["avg_score"] or 0), 2)

        # -- Proctoring Alerts -------------------------------------------------
        proctoring_qs = (
            ProctoringLog.objects
            .filter(
                attempt__quiz__course=course,
                event_type__in=self.CRITICAL_EVENT_TYPES,
            )
            .values("event_type")
            .annotate(count=Count("id"))
        )
        proctoring_alerts = {
            entry["event_type"]: entry["count"]
            for entry in proctoring_qs
        }

        # -- VARK Distribution -------------------------------------------------
        vark_qs = (
            LMSUser.objects
            .filter(pk__in=enrolled_student_ids)
            .values("vark_dominant")
            .annotate(count=Count("id"))
            .order_by("vark_dominant")
        )
        vark_distribution = {
            entry["vark_dominant"]: entry["count"]
            for entry in vark_qs
        }

        # -- Top Failed Concepts (All for the select) -------------------------
        all_failed_qs = (
            FailedTopic.objects
            .filter(evaluation__course=course)
            .values("concept_id")
            .annotate(fail_count=Count("id"))
            .order_by("-fail_count")
        )
        available_topics = [
            {"concept_id": entry["concept_id"], "fail_count": entry["fail_count"]}
            for entry in all_failed_qs
        ]

        # -- Student List -----------------------------------------------------
        students_qs = LMSUser.objects.filter(pk__in=enrolled_student_ids).values("id", "username")
        students = [
            {"id": s["id"], "username": s["username"]}
            for s in students_qs
        ]

        return Response({
            "course_id": course.pk,
            "course_code": course.code,
            "course_name": course.name,
            "total_enrolled_students": total_enrolled_students,
            "average_quiz_score": average_quiz_score,
            "proctoring_alerts": proctoring_alerts,
            "vark_distribution": vark_distribution,
            "top_failed_concepts": available_topics[:3],
            "available_topics": available_topics,
            "students": students,
        })
