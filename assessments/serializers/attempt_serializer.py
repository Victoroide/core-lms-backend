from rest_framework import serializers

from assessments.models import AttemptAnswer, QuizAttempt


class AttemptAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_choice_id = serializers.IntegerField()


class AttemptSubmitSerializer(serializers.Serializer):
    """Inbound payload for quiz submission. The student specifies the quiz
    and provides an array of question->choice mappings.
    """

    quiz_id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    answers = AttemptAnswerSerializer(many=True)


class AttemptResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "student",
            "quiz",
            "start_time",
            "end_time",
            "final_score",
            "is_submitted",
        ]
        read_only_fields = fields
