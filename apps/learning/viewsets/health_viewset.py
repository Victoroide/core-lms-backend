from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@swagger_auto_schema(
    method="get",
    operation_summary="Liveness probe.",
    operation_description=(
        "Public health check endpoint. Returns {status: ok} "
        "with no authentication required."
    ),
    tags=["System"],
    responses={200: "Application is healthy."},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Return application liveness status. No authentication required."""
    return Response({"status": "ok"})
