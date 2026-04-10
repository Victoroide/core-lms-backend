from rest_framework import serializers

from assessments.models import AnswerChoice, Question, Quiz


class AnswerChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerChoice
        fields = ["id", "text"]


class QuestionSerializer(serializers.ModelSerializer):
    choices = AnswerChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "concept_id", "order", "choices"]


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "course", "time_limit_minutes", "is_active", "question_count"]


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "course",
            "time_limit_minutes",
            "is_active",
            "questions",
        ]
