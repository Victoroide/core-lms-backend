from rest_framework import serializers

from apps.assessments.models import AnswerChoice, Question, Quiz


class AnswerChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerChoice
        fields = ["id", "text"]


class AnswerChoiceTutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerChoice
        fields = ["id", "text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    choices = AnswerChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "concept_id", "order", "choices"]


class QuestionTutorSerializer(serializers.ModelSerializer):
    choices = AnswerChoiceTutorSerializer(many=True)

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


class QuizTutorSerializer(serializers.ModelSerializer):
    topic = serializers.CharField(source="course.name", read_only=True)
    question_count = serializers.IntegerField(source="questions.count", read_only=True)
    questions = QuestionTutorSerializer(many=True, required=False)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "topic",
            "created_at",
            "course",
            "time_limit_minutes",
            "is_active",
            "question_count",
            "questions",
        ]

    def create(self, validated_data):
        questions_data = validated_data.pop("questions", [])
        quiz = Quiz.objects.create(**validated_data)
        for q_data in questions_data:
            choices_data = q_data.pop("choices", [])
            question = Question.objects.create(quiz=quiz, **q_data)
            for c_data in choices_data:
                AnswerChoice.objects.create(question=question, **c_data)
        return quiz

    def update(self, instance, validated_data):
        questions_data = validated_data.pop("questions", None)
        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.time_limit_minutes = validated_data.get(
            "time_limit_minutes", instance.time_limit_minutes
        )
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.save()

        if questions_data is not None:
            # Simple implementation: recreate questions
            instance.questions.all().delete()
            for q_data in questions_data:
                choices_data = q_data.pop("choices", [])
                question = Question.objects.create(quiz=instance, **q_data)
                for c_data in choices_data:
                    AnswerChoice.objects.create(question=question, **c_data)
        return instance
