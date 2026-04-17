from django.contrib import admin

from apps.assessments.models import (
    AnswerChoice,
    AttemptAnswer,
    ProctoringLog,
    Question,
    Quiz,
    QuizAttempt,
)


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 2


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "time_limit_minutes", "is_active", "created_at")
    list_filter = ("is_active", "course")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "concept_id", "order")
    list_filter = ("quiz",)
    inlines = [AnswerChoiceInline]


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0


class ProctoringLogInline(admin.TabularInline):
    model = ProctoringLog
    extra = 0


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("pk", "student", "quiz", "final_score", "is_submitted", "start_time")
    list_filter = ("is_submitted", "quiz")
    inlines = [AttemptAnswerInline, ProctoringLogInline]
