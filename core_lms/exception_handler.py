"""Global DRF exception handler returning JSON for all unhandled errors."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    """Convert any unhandled exception into a JSON 500 response.

    Delegates known DRF exceptions to the default handler. For anything
    else, logs the full traceback and returns a uniform JSON payload so
    the frontend never receives an HTML 500 page.

    Args:
        exc (Exception): The exception raised during view processing.
        context (dict): DRF-provided context with the view and request.

    Returns:
        Response: A JSON response with detail and appropriate status.
    """
    response = exception_handler(exc, context)
    if response is None:
        logger.exception(
            "Unhandled exception in view %s", context.get("view")
        )
        response = Response(
            {"detail": "An unexpected error occurred. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response
