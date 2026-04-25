# CU-11 — Revisar dashboard analítico del curso

## Overview

Tutors load a single endpoint that aggregates enrollment, average quiz score, critical proctoring alerts, VARK distribution, and the top failed concepts for a course. Angular fetches the dashboard through `CourseStore.loadCourseDashboard(courseId)` and the result feeds both the cognitive-graph form on `TutorDashboardPageComponent` and inline displays. Django computes the aggregates inside `TeacherDashboardViewSet.course_dashboard`, deliberately excluding `face_not_detected` from the proctoring totals to focus the alert surface on high-risk integrity events.

## Actors and Preconditions

- Actor: Tutor.
- The caller is authenticated with `activeRole = 'TUTOR'` on the client and `request.user.role == 'TUTOR'` on the server.
- The target course exists.
- Aggregates are computed on whatever data is present; missing assessments simply yield empty objects/arrays rather than 404.

## Frontend Entry Point

- Route: `/tutor` → `TutorDashboardPageComponent` ([src/app/pages/tutor/dashboard-page/tutor-dashboard-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/tutor/dashboard-page/tutor-dashboard-page.component.ts)). Also accessible from `/tutor/course/:courseId` → `TutorCourseViewerPageComponent`.
- Trigger:
  - Selecting a course in `<app-course-overview enableTutorAnalytics="true" />` calls `courseStore.selectCourse(courseId)` then `courseStore.loadCourseDashboard(courseId)`.
  - The dashboard auto-loads on page enter when a course is preselected; otherwise the tutor's "Reload All" button ([template line in the page] re-runs `loadCourseDashboard`).
- Display: dashboard data feeds the cognitive-graph topic seed list — the effect at lines 106-118 of `TutorDashboardPageComponent` watches `courseStore.selectedCourseDashboard()` and pushes `top_failed_concepts.map(c => c.concept_id)` into the `graphForm.topics` form control automatically.
- Inline display: the tutor course-viewer page also reads `courseStore.selectedCourseDashboard()` to render a "students enrolled / average score" header strip [verify: rendering present in `tutor-course-viewer.component.html` template].

## End-to-End Flow

1. Tutor opens `/tutor` (or `/tutor/course/:courseId`); the page constructor selects the course via `courseStore.selectCourse(courseId)` and calls `courseStore.loadCourseDashboard(courseId)`.
2. `CourseStore.loadCourseDashboard(courseId)` (signal store at [src/app/entities/course/model/course.store.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/model/course.store.ts)) sets `isLoadingDashboard=true` and awaits `firstValueFrom(courseApi.getCourseDashboard(courseId))`.
3. `CourseApiService.getCourseDashboard(courseId)` ([src/app/entities/course/api/course.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/api/course.api.ts)) calls `djangoApi.get<CourseDashboardSummary>('/api/v1/analytics/course/${courseId}/dashboard/')`.
4. `baseUrlInterceptor` resolves `environment.djangoApiUrl`; `authInterceptor` attaches the bearer token.
5. Django routes the request via `apps/assessments/urls.py` to `TeacherDashboardViewSet.course_dashboard` ([apps/assessments/viewsets/analytics_viewset.py](../../apps/assessments/viewsets/analytics_viewset.py) lines 86-233).
6. `permission_classes = [IsAuthenticated, IsTutor]` admits the request. The `@action(detail=False, methods=['get'], url_path=r'course/(?P<course_id>[^/.]+)/dashboard')` decorator binds the path.
7. The view resolves the course by PK; missing course returns HTTP 404 `{"error": "not_found", "detail": "Course not found."}`.
8. The view computes:
   - `total_enrolled_students` — set union of `Evaluation.student_id` and `QuizAttempt.student_id` for the course.
   - `average_quiz_score` — `Avg('final_score')` over submitted attempts (`is_submitted=True`).
   - `proctoring_alerts` — `ProctoringLog.objects.filter(attempt__quiz__course=course, event_type__in=CRITICAL_EVENT_TYPES).values('event_type').annotate(count=Count('id'))`. `CRITICAL_EVENT_TYPES = [TAB_SWITCHED, MULTIPLE_FACES]` (lines 98-101). `face_not_detected` is deliberately excluded.
   - `vark_distribution` — `LMSUser.objects.values('vark_dominant').annotate(count=Count('id'))` filtered to enrolled students.
   - `top_failed_concepts` — `FailedTopic.objects.values('concept_id').annotate(fail_count=Count('id')).order_by('-fail_count')`, top 3.
   - `available_topics` — same query without the top-3 cap.
   - `students` — id/username list of enrolled students.
9. The view returns `CourseDashboardSummary` as HTTP 200 JSON.
10. Angular `CourseStore` writes the response into `selectedCourseDashboard` and clears `isLoadingDashboard`.
11. `TutorDashboardPageComponent` effect detects the change and pushes `top_failed_concepts.map(c => c.concept_id)` into the cognitive-graph form's `topics` control (CU-12 then runs the graph fetch).

## Angular Implementation

- `CourseApiService.getCourseDashboard(courseId: number): Observable<CourseDashboardSummary>` — straight GET; no query parameters.
- Type: `CourseDashboardSummary` ([src/app/entities/course/model/course.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/model/course.types.ts)) — `{ course_id, course_code, course_name, total_enrolled_students, average_quiz_score, proctoring_alerts: Record<string, number>, vark_distribution: Record<string, number>, top_failed_concepts: FailedConceptItem[], available_topics: FailedConceptItem[], students: { id, username }[] }`. `FailedConceptItem = { concept_id, fail_count }`.
- `CourseStore.loadCourseDashboard(courseId)` — async; `patchState({ isLoadingDashboard: true, dashboardError: null })` then `firstValueFrom(courseApi.getCourseDashboard(courseId))`. On error patches `dashboardError`.
- `CourseStore.selectCourse(courseId)` resets `selectedCourseDashboard=null` first, so revisiting a course explicitly forces a re-fetch.
- `TutorDashboardPageComponent`:
  - Reactive `graphForm = fb.group({ studentId: ['', Validators.required], topics: [[], Validators.required], targetTopic: [''] })`.
  - Effect (constructor lines 106-118) watches `courseStore.selectedCourseDashboard()`; when it changes for a different `courseId` than the cached `lastDashboardCourseId`, it pushes the dashboard's `top_failed_concepts` into `graphForm.topics`.
  - `useSuggestedTopics()` is the explicit button-bound version of the same logic (sets `graphForm.topics` from `top_failed_concepts`).
- `<app-course-overview enableTutorAnalytics="true">` reads `courseStore.selectedCourseDashboard()` and surfaces the totals; concrete chart rendering is a future enhancement (the current template renders simple key/value lists). [verify: no PrimeNG Chart or D3 instance attached to the dashboard signals in this codebase.]
- Errors propagate through `courseStore.dashboardError()`; the apiErrorInterceptor logs to console and the apiErrorInterceptor does not raise toasts.

## Backend Implementation

- Endpoint: `GET /api/v1/analytics/course/{course_id}/dashboard/` (action route on the analytics router).
- Viewset: `TeacherDashboardViewSet` (`viewsets.ViewSet`) at [apps/assessments/viewsets/analytics_viewset.py](../../apps/assessments/viewsets/analytics_viewset.py) lines 86-233.
- Permissions: class-level `[IsAuthenticated, IsTutor]` (line 96). Action: `@action(detail=False, methods=['get'], url_path=r'course/(?P<course_id>[^/.]+)/dashboard')`.
- Constants: `CRITICAL_EVENT_TYPES = [ProctoringLog.EventType.TAB_SWITCHED, ProctoringLog.EventType.MULTIPLE_FACES]` (lines 98-101).
- Service: none; aggregation logic is inline in the action (lines 154-213).
- Models read: `learning.Course`, `learning.Evaluation`, `assessments.QuizAttempt`, `assessments.ProctoringLog`, `learning.LMSUser`, `learning.FailedTopic`.
- Status codes: 200 on success, 401 on missing JWT, 403 on non-tutor, 404 on missing course.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `learning.Course` | Read | Existence check and metadata source. |
| `learning.Evaluation` | Read | Contributes to `total_enrolled_students`. |
| `assessments.QuizAttempt` | Read | `Avg('final_score')` over submitted rows; contributes to enrolled set. |
| `assessments.ProctoringLog` | Read | Event counts grouped by `event_type ∈ CRITICAL_EVENT_TYPES`. |
| `learning.LMSUser` | Read | VARK distribution and student list. |
| `learning.FailedTopic` | Read | `concept_id` aggregation for `top_failed_concepts` and `available_topics`. |

## Technical Notes

- The endpoint intentionally excludes `face_not_detected` from `proctoring_alerts` by restricting counts to `CRITICAL_EVENT_TYPES`, emphasizing high-risk integrity signals (Corrigan-Gibbs et al., 2025).
- VARK distribution is aggregated from enrolled students to support pedagogy-aware cohort analysis around adaptive instruction planning (Alharbi et al., 2025).
- The dashboard exposes both `top_failed_concepts` (the top 3 for the at-a-glance UI) and `available_topics` (the full ranked list) so the tutor's cognitive-graph form can offer a multi-select picker without a second round-trip; `TutorDashboardPageComponent.useSuggestedTopics()` consumes this for CU-12 seeding.
- `total_enrolled_students` is computed from the union of evaluation owners and attempt owners. Students who only own `Submission` rows but never an evaluation or attempt are not counted; a future iteration could include submissions in the union.
- `average_quiz_score` is the mean of raw `final_score` values (not percentages), matching the storage convention from CU-09. Tutors interpreting the number need to divide by `max_score` to get a percentage; the field name does not communicate that distinction in the response.
- The `face_not_detected` event is still ingested into `ProctoringLog` (CU-09), so it remains queryable for forensic and threshold-tuning work; it is hidden from the dashboard alert aggregate only.
- The aggregation runs synchronously in a single request. For courses with very large `FailedTopic` cardinalities, the `Count` annotations may benefit from indexing or caching, but no caching layer is currently in place.
- Response field shapes are stable, so chart libraries can bind directly to `vark_distribution` and `proctoring_alerts` records without normalization. The current SPA renders them as text; PrimeNG Chart would be a drop-in upgrade.

## Request / Response

`GET /api/v1/analytics/course/12/dashboard/` — HTTP 200

```json
{
  "course_id": 12,
  "course_code": "CS-301",
  "course_name": "Advanced Programming",
  "total_enrolled_students": 10,
  "average_quiz_score": 3.4,
  "proctoring_alerts": {
    "tab_switched": 6,
    "multiple_faces": 2
  },
  "vark_distribution": {
    "visual": 3,
    "aural": 2,
    "read_write": 3,
    "kinesthetic": 2
  },
  "top_failed_concepts": [
    { "concept_id": "Polymorphism", "fail_count": 7 },
    { "concept_id": "Inheritance", "fail_count": 5 },
    { "concept_id": "Recursion", "fail_count": 4 }
  ],
  "available_topics": [
    { "concept_id": "Polymorphism", "fail_count": 7 },
    { "concept_id": "Inheritance", "fail_count": 5 },
    { "concept_id": "Recursion", "fail_count": 4 },
    { "concept_id": "Graphs", "fail_count": 2 }
  ],
  "students": [
    { "id": 2, "username": "alice" },
    { "id": 5, "username": "bob" }
  ]
}
```

Course not found (HTTP 404):

```json
{ "error": "not_found", "detail": "Course not found." }
```
