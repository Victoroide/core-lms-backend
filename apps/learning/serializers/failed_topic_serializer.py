from rest_framework import serializers

from apps.learning.models import FailedTopic


class FailedTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = FailedTopic
        fields = ["id", "concept_id", "score", "max_score"]
        read_only_fields = ["id"]
