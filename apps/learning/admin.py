from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.learning.models import (
    LMSUser,
    Course,
    Evaluation,
    FailedTopic,
    EvaluationTelemetry,
    Career,
    Semester,
    Module,
    Lesson,
    Resource,
)


@admin.register(LMSUser)
class LMSUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "vark_dominant", "is_active")
    list_filter = ("role", "vark_dominant", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("EdTech Profile", {"fields": ("role", "vark_dominant")}),
    )


# ---------------------------------------------------------------------------
# Academic Ontology Inlines
# ---------------------------------------------------------------------------


class SemesterInline(admin.StackedInline):
    model = Semester
    extra = 0


class ModuleInline(admin.StackedInline):
    model = Module
    extra = 0


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 0


class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 0


# ---------------------------------------------------------------------------
# Academic Ontology Admin
# ---------------------------------------------------------------------------


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")
    inlines = [SemesterInline]


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "career", "number", "year", "period", "created_at")
    list_filter = ("career", "period", "year")
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "semester", "created_at")
    list_filter = ("semester",)
    search_fields = ("code", "name")
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = ("course",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "order")
    list_filter = ("module__course",)
    inlines = [ResourceInline]


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "resource_type", "uploaded_by", "created_at")
    list_filter = ("resource_type",)


# ---------------------------------------------------------------------------
# Evaluation Admin (existing)
# ---------------------------------------------------------------------------


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
