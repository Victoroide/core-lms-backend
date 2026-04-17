"""Serializer for the EvaluationTelemetry dedicated endpoint."""

from rest_framework import serializers

from apps.learning.models import EvaluationTelemetry


class EvaluationTelemetrySerializer(serializers.ModelSerializer):
    """Serializer for EvaluationTelemetry CRUD operations.

    Exposes the evaluation FK for create and the telemetry payload
    fields for read operations.
    """

    class Meta:
        """Meta options for EvaluationTelemetrySerializer."""

        model = EvaluationTelemetry
        fields = ["id", "evaluation", "time_on_task_seconds", "clicks"]
        read_only_fields = ["id"]
