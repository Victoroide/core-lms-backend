"""Rate-limited JWT token authentication view."""

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class RateLimitedTokenView(TokenObtainPairView):
    """JWT token obtain endpoint with per-IP rate limiting.

    Limits POST /api/v1/auth/token/ to 10 requests per minute per IP
    to mitigate credential-stuffing and brute-force attacks. Exceeding
    the limit returns HTTP 429 Too Many Requests.
    """

    # ``block=False`` lets us inspect ``request.limited`` and return 429
    # directly instead of the framework's default 403 PermissionDenied.
    @swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Obtain JWT access and refresh tokens.",
        operation_description=(
            "Authenticate with username and password to receive an access "
            "token (30 min lifetime) and refresh token (7 days). Rate limited "
            "to 10 requests per minute per IP."
        ),
        responses={
            200: "Access and refresh tokens returned successfully.",
            401: "Invalid credentials.",
            429: "Too many login attempts. Rate limit exceeded.",
        },
    )
    @method_decorator(
        ratelimit(key="ip", rate="10/m", method="POST", block=False)
    )
    def post(self, request, *args, **kwargs):
        """Issue access and refresh tokens if credentials are valid.

        Args:
            request (Request): The incoming HTTP request with credentials.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: Token pair on success, 401 on invalid credentials,
                429 when the rate limit is exceeded.
        """
        if getattr(request, "limited", False):
            return Response(
                {"detail": "Too many login attempts. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return super().post(request, *args, **kwargs)


class TaggedTokenRefreshView(TokenRefreshView):
    """Refresh endpoint wrapper adding a proper Swagger tag."""

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Rotate refresh token and return new access token.",
        operation_description=(
            "Exchanges a valid refresh token for a new access+refresh pair. "
            "The previous refresh token is blacklisted immediately "
            "(rotation + blacklist)."
        ),
        responses={
            200: "New access and refresh tokens.",
            401: "Invalid or blacklisted refresh token.",
        },
    )
    def post(self, request, *args, **kwargs):
        """Refresh the JWT access token using a valid refresh token."""
        return super().post(request, *args, **kwargs)
