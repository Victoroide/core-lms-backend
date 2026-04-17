import logging

import requests
from django.conf import settings

from apps.learning.models import Evaluation
from apps.learning.services.exceptions import AxiomEngineError

logger = logging.getLogger(__name__)

AXIOM_TIMEOUT = (3, 10)


class AxiomEngineClient:
    """HTTP client for the AxiomEngine Go microservice.

    Translates the rigorous Django evaluation dataset into the flattened payload
    contract expected by POST /api/v1/adaptive-plan, executes the synchronous HTTP request,
    and parses the returned JSON payload.

    Connection failures and timeouts are handled gracefully: a fallback dict
    is returned so that quiz scoring never crashes due to AxiomEngine unavailability.
    """

    def __init__(self):
        """Initialize the client with the base URL from Django settings.

        Raises:
            django.core.exceptions.ImproperlyConfigured: If AXIOM_ENGINE_URL is missing.
        """
        self.base_url = settings.AXIOM_ENGINE_URL.rstrip("/")

    def request_adaptive_plan(self, evaluation_id: int) -> dict:
        """Build the payload from database records and dispatch HTTP POST to AxiomEngine.

        On ConnectionError or Timeout, returns a fallback dict with
        ``{"plan": [], "fallback": True}`` instead of raising. Non-2xx
        responses still raise ``AxiomEngineError``.

        Args:
            evaluation_id (int): The primary key of the Evaluation record.

        Returns:
            dict: The adaptive study plan from AxiomEngine, or a fallback dict.

        Raises:
            AxiomEngineError: If the Go microservice returns a non-2xx status code.
            Evaluation.DoesNotExist: If the evaluation_id does not exist.
        """
        evaluation = (
            Evaluation.objects
            .select_related("student", "course")
            .prefetch_related("failed_topics")
            .get(pk=evaluation_id)
        )

        telemetry_data = {}
        if hasattr(evaluation, "telemetry"):
            tel = evaluation.telemetry
            telemetry_data = {
                "session_id": f"eval-{evaluation.pk}",
                "timestamp_unix": int(evaluation.created_at.timestamp()),
                "duration_ms": tel.time_on_task_seconds * 1000.0,
                "client_version": "django-lms-1.0",
            }

        failed_concept_ids = list(
            evaluation.failed_topics.values_list("concept_id", flat=True)
        )

        payload = {
            "student_id": str(evaluation.student.pk),
            "course_id": evaluation.course.code,
            "failed_topics": failed_concept_ids,
            "vark_profile": evaluation.student.vark_dominant,
        }
        if telemetry_data:
            payload["telemetry"] = telemetry_data

        url = f"{self.base_url}/api/v1/adaptive-plan"

        logger.info(
            "AxiomEngine request: url=%s student=%s topics=%s",
            url,
            payload["student_id"],
            failed_concept_ids,
        )

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=AXIOM_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
        except requests.exceptions.Timeout as exc:
            logger.warning(
                "AxiomEngine timeout for eval %d: %s", evaluation_id, exc
            )
            return {"plan": [], "fallback": True}
        except requests.exceptions.ConnectionError as exc:
            logger.warning(
                "AxiomEngine connection error for eval %d: %s",
                evaluation_id,
                exc,
            )
            return {"plan": [], "fallback": True}

        if not response.ok:
            logger.error(
                "AxiomEngine error: status=%d body=%s",
                response.status_code,
                response.text[:500],
            )
            raise AxiomEngineError(
                status_code=response.status_code,
                detail=response.text[:500],
            )

        result = response.json()
        logger.info(
            "AxiomEngine success: items=%d latency_ms=%s",
            len(result.get("items", [])),
            result.get("_meta", {}).get("total_latency_ms"),
        )
        return result

