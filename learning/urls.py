from rest_framework.routers import DefaultRouter

from learning.viewsets import EvaluationViewSet, UserViewSet

router = DefaultRouter()
router.register(r"evaluations", EvaluationViewSet, basename="evaluation")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = router.urls
