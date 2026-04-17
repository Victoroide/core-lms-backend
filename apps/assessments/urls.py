from rest_framework.routers import DefaultRouter

from apps.assessments.viewsets import (
    AttemptViewSet,
    EvaluationTelemetryViewSet,
    ProctoringViewSet,
    QuizViewSet,
    TeacherDashboardViewSet,
)

router = DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"attempts", AttemptViewSet, basename="attempt")
router.register(r"proctoring/logs", ProctoringViewSet, basename="proctoring-log")
router.register(r"analytics", TeacherDashboardViewSet, basename="analytics")
router.register(
    r"evaluation-telemetry",
    EvaluationTelemetryViewSet,
    basename="evaluation-telemetry",
)

urlpatterns = router.urls
