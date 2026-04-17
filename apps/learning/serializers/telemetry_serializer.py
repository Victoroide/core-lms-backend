from rest_framework import serializers

from apps.learning.models import EvaluationTelemetry


class TelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationTelemetry
        fields = ["time_on_task_seconds", "clicks"]
