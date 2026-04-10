from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

schema_view = get_schema_view(
    openapi.Info(
        title="Core LMS API",
        default_version="v1",
        description=(
            "University EdTech MVP -- Core Learning Management System.\n\n"
            "## Authentication\n"
            "All endpoints require a valid JWT unless otherwise noted.\n\n"
            "1. POST `/api/v1/auth/token/` with `username` and `password` to obtain an access token.\n"
            "2. Click **Authorize** above and enter: `Bearer <access_token>`.\n"
            "3. Click **Authorize** to persist the token for all subsequent requests.\n"
        ),
        contact=openapi.Contact(email="lms-dev@university.edu"),
        license=openapi.License(name="MIT"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- JWT Authentication ------------------------------------------------
    path(
        "api/v1/auth/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/v1/auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # --- Application routes ------------------------------------------------
    path("api/v1/", include("learning.urls")),
    path("api/v1/", include("assessments.urls")),

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
