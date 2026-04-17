from rest_framework.routers import DefaultRouter

from apps.curriculum.viewsets import AssignmentViewSet, SubmissionViewSet

router = DefaultRouter()
router.register(r"assignments", AssignmentViewSet, basename="assignment")
router.register(r"submissions", SubmissionViewSet, basename="submission")

urlpatterns = router.urls
