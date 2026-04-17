from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from apps.learning.viewsets.auth_viewset import (
    RateLimitedTokenView,
    TaggedTokenRefreshView,
)
from apps.learning.viewsets.health_viewset import health_check

schema_view = get_schema_view(
    openapi.Info(
        title="AxiomLMS Core API",
        default_version="v1",
        description=(
            "Core LMS API -- academic ontology, evaluation, proctoring, "
            "adaptive study plans."
        ),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- Health check (public, no auth) ------------------------------------
    path("health/", health_check),

    # --- JWT Authentication ------------------------------------------------
    path(
        "api/v1/auth/token/",
        RateLimitedTokenView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/v1/auth/token/refresh/",
        TaggedTokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # --- Application routes ------------------------------------------------
    path("api/v1/", include("apps.learning.urls")),
    path("api/v1/", include("apps.assessments.urls")),
    path("api/v1/", include("apps.curriculum.urls")),

    # --- Documentation -----------------------------------------------------
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]
