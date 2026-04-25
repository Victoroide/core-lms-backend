# CU-03 — Gestionar jerarquía académica

## Overview

Tutors maintain the `Career → Semester → Course → Module → Lesson` ontology while authenticated users consume it for navigation and lesson content. Angular reads the catalog via `CourseStore`, drives course detail navigation through `/student/course/:courseId` or `/tutor/course/:courseId`, and renders nested module/lesson trees inside the course viewer pages. Django serves the hierarchy through five `ModelViewSet` classes in the `learning` app, applies `IsTutor` to mutating actions, and uses `SoftDeleteMixin` so deletions hide rows from the default queryset without removing them.

## Actors and Preconditions

- Actors: Tutor (CRUD), Student (read), any authenticated `LMSUser` (read).
- The caller is authenticated; `roleGuard` verifies `data.role` matches `sessionStore.activeRole()` for `/student/*` and `/tutor/*` route subtrees.
- Mutating endpoints require `request.user.role == 'TUTOR'` (`IsTutor` permission class).
- For child-resource creation, the parent FK must already exist (e.g., `Career` before `Semester`).

## Frontend Entry Point

- Read entry route (student): `/student` → `StudentDashboardPageComponent` → `<app-course-overview />`.
- Read entry route (tutor): `/tutor` → `TutorDashboardPageComponent` → `<app-course-overview enableTutorAnalytics="true" />`.
- Detail route: `/student/course/:courseId` → `CourseViewerPageComponent` ([src/app/pages/student/course-viewer-page/course-viewer-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/student/course-viewer-page/course-viewer-page.component.ts)) and `/tutor/course/:courseId` → `TutorCourseViewerPageComponent`.
- Trigger:
  - Listing — `CourseOverviewComponent` ([src/app/features/course/course-overview/course-overview.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/course/course-overview/course-overview.component.ts)) calls `courseStore.loadCourses()` from its constructor.
  - Detail navigation — clicking a course card in `CourseOverviewComponent.navigateToCourse(courseId)`.
  - Detail load — `CourseViewerPageComponent` constructor subscribes to `route.paramMap` and calls `courseStore.loadCourseDetail(courseId)`.
  - Mutations — `TutorCourseViewerPageComponent` exposes a quiz-creation dialog and the same modules/lessons tree, but the Angular code in this repository does **not** ship dedicated CRUD forms for `Career`, `Semester`, `Course`, or `Module`/`Lesson`. Tutors mutate the hierarchy through Django admin or directly via the REST endpoints (verified absent: no `careers/edit` or `lessons/create` UI).

## End-to-End Flow

1. The component constructor calls `courseStore.loadCourses()` (or `loadCourseDetail(id)` for a detail view).
2. `CourseStore.loadCourses` (signal store at [src/app/entities/course/model/course.store.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/model/course.store.ts)) sets `isLoading=true` and awaits `firstValueFrom(courseApi.listCourses(params))`.
3. `CourseApiService.listCourses` ([src/app/entities/course/api/course.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/api/course.api.ts)) calls `djangoApi.get<PaginatedResponse<CourseListItem>>('/api/v1/courses/', { params: { semester, semester__career } })`.
4. `baseUrlInterceptor` resolves the URL against `environment.djangoApiUrl`; `authInterceptor` attaches the bearer token.
5. Django dispatches via `apps/learning/urls.py` to `CourseViewSet` in `apps/learning/viewsets/course_viewset.py`. `get_permissions()` returns `[IsAuthenticated()]` for `list`.
6. `CourseViewSet.get_queryset()` applies `select_related("semester__career")` and `prefetch_related("modules__lessons__resources")` only on `retrieve`; `list` returns `Course.objects.all()` filtered by the default `SoftDeleteManager`.
7. `CourseListSerializer` serializes the rows and DRF's `PageNumberPagination` (PAGE_SIZE=20) wraps them into `{ count, next, previous, results }`.
8. `CourseStore` extracts `response.results` into the `courses` signal and clears `isLoading`.
9. On a course click, `CourseOverviewComponent.navigateToCourse(courseId)` calls `router.navigate(['/student/course', courseId])` (or `/tutor/course/...` based on role).
10. `CourseViewerPageComponent` fires `courseStore.selectCourse(courseId)` then `courseStore.loadCourseDetail(courseId)`, which calls `courseApi.getCourseDetail(courseId)` against `/api/v1/courses/${courseId}/`.
11. Django dispatches to `CourseViewSet.retrieve`; `CourseDetailSerializer` returns the course with nested `semester` and a `modules` method field that recursively embeds lessons with resources.
12. `CourseStore` populates `selectedCourseDetail` and the page template iterates `courseModules()` to render the sidebar tree of modules and lessons.
13. Selecting a lesson in the sidebar calls `selectLesson(lesson)` which sets a local `signal<LessonItem | null>(null)` and renders `<app-lesson-viewer [lesson]="selectedLesson()!" />` (CU-04 covers lesson resource loading).
14. For mutations through admin tooling, Django routes write requests to the same viewsets; `get_permissions()` returns `[IsTutor()]`, `destroy` calls `instance.delete()` which `SoftDeleteMixin.delete` rewrites as `is_deleted=True`, `deleted_at=now()`. Subsequent reads omit those rows because the default manager is `SoftDeleteManager`.

## Angular Implementation

- `CourseApiService.listCourses(params?: { semester?: number; career?: number }): Observable<PaginatedResponse<CourseListItem>>` — note: the `career` param is forwarded as `semester__career` per Django filterset.
- `CourseApiService.getCourseDetail(courseId: number): Observable<CourseDetail>`.
- `CourseStore` (signal store, `providedIn: 'root'`) state: `courses: CourseListItem[]`, `selectedCourseId: number | null`, `selectedCourseDetail: CourseDetail | null`, `selectedCourseDashboard`, `selectedCourseQuizzes`, `isLoading`, `isLoadingDashboard`, `isLoadingQuizzes`, `error`, `dashboardError`. Computed: `selectedCourse` (derived from id+list).
- Methods: `loadCourses()`, `selectCourse(courseId)`, `loadCourseDetail(courseId)`, `loadCourseDashboard(courseId)` (CU-11), `loadCourseQuizzes(courseId)` (CU-08).
- `CourseOverviewComponent` reads `courseStore.courses()`, `courseStore.selectedCourseDetail()`, `courseStore.selectedCourseQuizzes()`. The `@Input() inline = false` flag toggles between expanding the card in place vs routing to the dedicated viewer page.
- `CourseViewerPageComponent` accepts `courseId` from `ActivatedRoute.paramMap`. It uses local `signal<LessonItem | null>(null)` for `selectedLesson`, computed `courseName` and `courseModules` from `courseStore.selectedCourseDetail()`, and `<details>` HTML elements for the expandable sidebar.
- No reactive form group exists in either viewer page for ontology mutations; the tutor-side viewer hosts only the quiz editor (CU-08) and the grading panel (CU-07).
- Errors propagate through `courseStore.error()` and are rendered as plain text; the `apiErrorInterceptor` only logs.

## Backend Implementation

- Endpoints (registered via DRF router in `apps/learning/urls.py`):
  - `/api/v1/careers/` → `CareerViewSet` (`apps/learning/viewsets/career_viewset.py`).
  - `/api/v1/semesters/` → `SemesterViewSet`.
  - `/api/v1/courses/` → `CourseViewSet`.
  - `/api/v1/modules/` → `ModuleViewSet`.
  - `/api/v1/lessons/` → `LessonViewSet`.
- Each viewset is a `ModelViewSet`; `get_permissions()` returns `[IsAuthenticated()]` for safe methods and `[IsTutor()]` for `create / update / partial_update / destroy`.
- Serializers:
  - List/create/update — `CareerSerializer`, `SemesterSerializer`, `CourseListSerializer`, `ModuleSerializer`, `LessonSerializer`.
  - Retrieve — `CareerDetailSerializer` (embeds semesters), `CourseDetailSerializer` (embeds full module/lesson/resource tree), `LessonDetailSerializer` (embeds resources).
- Filtering: each viewset declares `filterset_fields` for the obvious parent FK (`career`, `semester`, `semester__career`, `course`, `module`) plus `is_deleted` so admins can opt into the soft-deleted queryset.
- Soft delete: `instance.delete()` is intercepted by `SoftDeleteMixin.delete` (`core_lms/mixins.py`) which assigns `is_deleted=True` and `deleted_at=timezone.now()`. The default manager `SoftDeleteManager` filters them out; `all_objects` exposes them.
- Status codes: 200 on read, 201 on create, 200 on update/partial_update, 204 on (soft) delete, 400 on serializer validation failure, 403 on non-tutor write.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `learning.Career` | Read / Write / Soft delete | `code` is unique; one of the eight soft-delete models. |
| `learning.Semester` | Read / Write / Soft delete | `unique_together = (career, number, year)`. |
| `learning.Course` | Read / Write / Soft delete | `code` unique; FK to `Semester` is nullable with `SET_NULL`. |
| `learning.Module` | Read / Write / Soft delete | Ordered child of `Course` via `order` field. |
| `learning.Lesson` | Read / Write / Soft delete | Ordered child of `Module`; `LessonDetailSerializer` embeds resources. |

## Technical Notes

- The default manager hides soft-deleted rows; admin or audit traffic must opt in via `?is_deleted=true` or use `Model.all_objects`.
- `CourseDetailSerializer.modules` is a `SerializerMethodField` that walks `prefetch_related("modules__lessons__resources")`, so the retrieve endpoint returns the full tree in one round-trip and the Angular sidebar renders without further calls.
- `CourseStore.loadCourseDetail` does not block on `loadCourses` — both can run independently. The course-detail page does not assume the listing has been fetched.
- Mutating endpoints exist in Django but the Angular SPA does not expose CRUD UI for `Career`, `Semester`, `Course`, `Module`, `Lesson` ontology. Tutors that need to create or edit these entities use Django admin (`/admin/`) or the REST endpoints directly.
- The `roleGuard` does not differentiate between `STUDENT` and `TUTOR` for ontology reads — both can list and retrieve. The split exists at the Django permission layer for writes only.
- `CourseApiService.listCourses` forwards `career` as `semester__career` because Django's filterset declares the lookup as `semester__career`; the client renames the key transparently before sending.

## Request / Response

`GET /api/v1/courses/?semester=3` — HTTP 200

Response (paginated list):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 12,
      "semester": 3,
      "name": "Advanced Programming",
      "code": "CS-301",
      "description": "Object-oriented design and applied data structures",
      "created_at": "2026-04-25T15:42:11.223874Z"
    }
  ]
}
```

`GET /api/v1/courses/12/` — HTTP 200 (nested detail)

```json
{
  "id": 12,
  "semester": {
    "id": 3,
    "career": 1,
    "name": "Semester 3",
    "number": 3,
    "year": 2026,
    "period": "I",
    "created_at": "2026-01-10T08:00:00Z"
  },
  "name": "Advanced Programming",
  "code": "CS-301",
  "description": "Object-oriented design and applied data structures",
  "created_at": "2026-04-25T15:42:11.223874Z",
  "modules": [
    {
      "id": 21,
      "course": 12,
      "title": "Object-Oriented Foundations",
      "description": "Classes, objects, inheritance",
      "order": 1,
      "lessons": [
        {
          "id": 55,
          "module": 21,
          "title": "Polymorphism",
          "content": "...",
          "order": 1,
          "resources": []
        }
      ]
    }
  ]
}
```

`POST /api/v1/courses/` — HTTP 201 (tutor-only)

Request:

```json
{
  "semester": 3,
  "name": "Advanced Programming",
  "code": "CS-301",
  "description": "Object-oriented design and applied data structures"
}
```

Response: same shape as the listing entry above plus `created_at`.

`DELETE /api/v1/courses/12/` — HTTP 204 (soft delete; row remains with `is_deleted=true`).
