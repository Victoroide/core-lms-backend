import logging

import requests
from django.conf import settings

from learning.models import Evaluation
from learning.services.exceptions import AxiomEngineError, AxiomEngineTimeout

logger = logging.getLogger(__name__)

AXIOM_TIMEOUT = (5, 25)


class AxiomEngineClient:
    """HTTP client for the AxiomEngine Go microservice.

    Translates the rich Django evaluation data into the flat payload
    contract expected by POST /api/v1/adaptive-plan, executes the request,
    and returns the parsed JSON response.
    """

    def __init__(self):
        self.base_url = settings.AXIOM_ENGINE_URL.rstrip("/")

    def request_adaptive_plan(self, evaluation_id: int) -> dict:
        """Build the payload from DB records and POST to AxiomEngine.

        Returns the parsed JSON response from the Go microservice containing
        the adaptive study plan and pipeline metadata.

        Raises:
            AxiomEngineTimeout: if the request exceeds AXIOM_TIMEOUT.
            AxiomEngineError: if the Go service returns a non-2xx status.
            Evaluation.DoesNotExist: if evaluation_id is invalid.
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
            logger.error("AxiomEngine timeout: %s", exc)
            raise AxiomEngineTimeout(url=url, timeout=AXIOM_TIMEOUT) from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("AxiomEngine connection error: %s", exc)
            raise AxiomEngineError(
                status_code=502,
                detail=f"Cannot connect to AxiomEngine at {url}",
            ) from exc

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
