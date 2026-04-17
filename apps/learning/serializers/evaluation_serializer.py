from rest_framework import serializers

from apps.learning.models import Evaluation, FailedTopic, EvaluationTelemetry
from apps.learning.serializers.failed_topic_serializer import FailedTopicSerializer
from apps.learning.serializers.telemetry_serializer import TelemetrySerializer


class EvaluationSerializer(serializers.ModelSerializer):
    """Writable nested serializer that creates an Evaluation along with
    its related FailedTopic and EvaluationTelemetry records in a single
    POST request from the Angular frontend.
    """

    failed_topics = FailedTopicSerializer(many=True)
    telemetry = TelemetrySerializer(required=False)

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "student",
            "course",
            "score",
            "max_score",
            "created_at",
            "failed_topics",
            "telemetry",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        failed_topics_data = validated_data.pop("failed_topics", [])
        telemetry_data = validated_data.pop("telemetry", None)

        evaluation = Evaluation.objects.create(**validated_data)

        for topic_data in failed_topics_data:
            FailedTopic.objects.create(evaluation=evaluation, **topic_data)

        if telemetry_data:
            EvaluationTelemetry.objects.create(
                evaluation=evaluation, **telemetry_data
            )

        return evaluation
