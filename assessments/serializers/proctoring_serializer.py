from rest_framework import serializers

from assessments.models import ProctoringLog


class ProctoringLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProctoringLog
        fields = ["id", "attempt", "event_type", "timestamp", "severity_score"]
        read_only_fields = ["id"]


class ProctoringBulkSerializer(serializers.Serializer):
    """Accepts an array of proctoring events for high-throughput ingestion
    from the frontend face-api.js pipeline.
    """

    events = ProctoringLogSerializer(many=True)
