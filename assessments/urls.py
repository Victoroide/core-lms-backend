from rest_framework.routers import DefaultRouter

from assessments.viewsets import (
    AttemptViewSet,
    ProctoringViewSet,
    QuizViewSet,
    TeacherDashboardViewSet,
)

router = DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"attempts", AttemptViewSet, basename="attempt")
router.register(r"proctoring/logs", ProctoringViewSet, basename="proctoring-log")
router.register(r"analytics", TeacherDashboardViewSet, basename="analytics")

urlpatterns = router.urls
