from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from learning.models import (
    LMSUser,
    Course,
    Evaluation,
    FailedTopic,
    EvaluationTelemetry,
)


@admin.register(LMSUser)
class LMSUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "vark_dominant", "is_active")
    list_filter = ("role", "vark_dominant", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("EdTech Profile", {"fields": ("role", "vark_dominant")}),
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")


class FailedTopicInline(admin.TabularInline):
    model = FailedTopic
    extra = 0


class TelemetryInline(admin.StackedInline):
    model = EvaluationTelemetry
    extra = 0


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("pk", "student", "course", "score", "max_score", "created_at")
    list_filter = ("course",)
    inlines = [FailedTopicInline, TelemetryInline]
