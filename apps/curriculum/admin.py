from django.contrib import admin

from apps.curriculum.models import Assignment, Submission


class SubmissionInline(admin.TabularInline):
    model = Submission
    extra = 0
    readonly_fields = ("submitted_at",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "created_by", "due_date", "max_score", "created_at")
    list_filter = ("lesson__module__course", "created_by")
    search_fields = ("title",)
    inlines = [SubmissionInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("pk", "assignment", "student", "submitted_at", "grade", "graded_at")
    list_filter = ("assignment", "student")
    readonly_fields = ("submitted_at",)
