from rest_framework.routers import DefaultRouter

from apps.learning.viewsets import (
    CertificateViewSet,
    EvaluationViewSet,
    UserViewSet,
    CareerViewSet,
    SemesterViewSet,
    CourseViewSet,
    ModuleViewSet,
    LessonViewSet,
    ResourceViewSet,
)

router = DefaultRouter()
router.register(r"evaluations", EvaluationViewSet, basename="evaluation")
router.register(r"users", UserViewSet, basename="user")
router.register(r"careers", CareerViewSet, basename="career")
router.register(r"semesters", SemesterViewSet, basename="semester")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"modules", ModuleViewSet, basename="module")
router.register(r"lessons", LessonViewSet, basename="lesson")
router.register(r"resources", ResourceViewSet, basename="resource")
router.register(r"certificates", CertificateViewSet, basename="certificate")

urlpatterns = router.urls
