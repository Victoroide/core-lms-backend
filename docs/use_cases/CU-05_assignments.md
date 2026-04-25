# CU-05 — Gestionar asignaciones

## Overview

Tutors create and maintain assignment definitions linked to lessons; students consume them inside the lesson viewer to know what file deliverable is expected. Angular fetches assignments lazily per lesson via `AssignmentApiService.getAssignmentsByLesson`, and Django CRUDs `curriculum.Assignment` rows through `AssignmentViewSet` with `IsTutor` on writes. Soft delete preserves audit history.

## Actors and Preconditions

- Actors: Tutor (create / read / update / soft-delete), Student (read).
- The caller is authenticated. Mutations require role `TUTOR`.
- The referenced lesson exists in the academic hierarchy.
- For students, the assignment is reached only through the lesson viewer; there is no top-level assignments page in Angular.

## Frontend Entry Point

- Read entry: `/student/course/:courseId` or `/tutor/course/:courseId` → respective course-viewer page → sidebar lesson click → `<app-lesson-viewer />` for students, `<app-grading-panel />` for tutors.
- Components:
  - Student-side read: `LessonViewerComponent` ([src/app/features/course/lesson-viewer/lesson-viewer.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/course/lesson-viewer/lesson-viewer.component.ts)) calls `AssignmentApiService.getAssignmentsByLesson(lessonId)` from `loadAssignmentData(lessonId)` in `ngOnChanges`.
  - Tutor-side read: `GradingPanelComponent` ([src/app/features/tutor/grading-panel/grading-panel.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/tutor/grading-panel/grading-panel.component.ts)) does the same.
- Trigger: `OnChanges` lifecycle hook fires whenever the parent page rebinds the `[lesson]` input — that happens whenever the user clicks a different lesson in the sidebar.
- Tutor-side mutation UI: there is no dedicated "Create Assignment" form in this codebase. Tutors create or edit assignments through Django admin or direct REST calls. [verify: no `assignment-editor` component found under `src/app/features/tutor/`].

## End-to-End Flow

1. The user clicks a lesson in the course-viewer sidebar; the parent rebinds `[lesson]` on `LessonViewerComponent` or `GradingPanelComponent`.
2. `ngOnChanges` resets local signals and calls `loadAssignmentData(lessonId)`.
3. `AssignmentApiService.getAssignmentsByLesson(lessonId)` ([src/app/entities/course/api/assignment.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/api/assignment.api.ts)) calls `djangoApi.get<PaginatedDjangoResponse<AssignmentItem>>('/api/v1/assignments/?lesson=${lessonId}')` and `map`s `response.results`.
4. `baseUrlInterceptor` prepends `environment.djangoApiUrl`; `authInterceptor` attaches the bearer token.
5. Django routes `GET /api/v1/assignments/?lesson=<id>` via `apps/curriculum/urls.py` to `AssignmentViewSet.list` ([apps/curriculum/viewsets/assignment_viewset.py](../../apps/curriculum/viewsets/assignment_viewset.py)).
6. `AssignmentViewSet.get_permissions()` returns `[IsAuthenticated()]` for safe methods; `filterset_fields = ['lesson', 'created_by', 'is_deleted']` allows the `?lesson=` lookup.
7. `AssignmentViewSet.get_queryset()` applies `select_related('lesson__module__course', 'created_by')` and the default `SoftDeleteManager` already excludes soft-deleted rows.
8. `AssignmentSerializer` returns `[id, lesson, created_by, title, description, due_date, max_score, created_at]`.
9. Angular receives the paginated envelope and the component stores the first row in `assignment = signal<AssignmentItem | null>(null)`. The lesson-viewer template branches on whether the assignment exists.
10. For tutor mutations through admin or scripted REST calls, `POST /api/v1/assignments/` enters `AssignmentViewSet.create`. `get_permissions()` returns `[IsTutor()]`, the serializer validates the payload, and the row is inserted into `curriculum.Assignment`.
11. `DELETE /api/v1/assignments/{id}/` calls `instance.delete()`, which `SoftDeleteMixin.delete` rewrites as `is_deleted=True`, `deleted_at=timezone.now()`. Subsequent reads omit it.

## Angular Implementation

- `AssignmentApiService.getAssignmentsByLesson(lessonId: number): Observable<AssignmentItem[]>` — extracts `response.results` from `PaginatedDjangoResponse<AssignmentItem>` via `map`.
- Type: `AssignmentItem = { id, lesson, title, description, due_date, max_score }` per [src/app/entities/course/model/assignment.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/model/assignment.types.ts).
- No store layer for assignments — components consume the Observable directly via `firstValueFrom` in `async` methods, then write the result into a `signal<AssignmentItem | null>(null)`.
- `LessonViewerComponent.loadAssignmentData(lessonId)` (private async) calls `assignmentApi.getAssignmentsByLesson(lessonId)` then chains `assignmentApi.getSubmissionsByAssignment(assignment.id)` to display the student's previous submission (CU-06).
- `GradingPanelComponent.loadAssignmentAndSubmissions(lessonId)` mirrors the same pattern but stores all submissions in a `signal<SubmissionItem[]>([])` and pre-populates a `Map<submissionId, gradeValue>` for inline grading (CU-07).
- Errors surface as `console.error` from `apiErrorInterceptor`; both components leave `assignment = null` on failure and the template falls back to "no assignment" copy.

## Backend Implementation

- Endpoint: `/api/v1/assignments/` (DRF router registration in `apps/curriculum/urls.py`) → `AssignmentViewSet` at [apps/curriculum/viewsets/assignment_viewset.py](../../apps/curriculum/viewsets/assignment_viewset.py).
- Permissions: `get_permissions()` returns `[IsAuthenticated()]` for safe methods and `[IsTutor()]` for `create / update / partial_update / destroy`.
- Serializer: `AssignmentSerializer` (`apps/curriculum/serializers/assignment_serializer.py`) with fields `[id, lesson, created_by, title, description, due_date, max_score, created_at]`; read-only `[id, created_at]`. `max_score` defaults to `100.00`.
- Service: none; CRUD is handled directly by `ModelViewSet`.
- Filterset: `lesson`, `created_by`, `is_deleted`.
- Models touched: `learning.Lesson` (FK validation), `learning.LMSUser` (`created_by` FK), `curriculum.Assignment` (write/read; soft-delete capable).
- Status codes: 200 on list/retrieve, 201 on create, 200 on update, 204 on soft delete, 400 on validation failure, 401 on missing JWT, 403 on non-tutor write.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `learning.Lesson` | Read | FK validation on assignment create/update. |
| `learning.LMSUser` | Read | `created_by` FK validation; not forced to `request.user`. |
| `curriculum.Assignment` | Create / Read / Update / Soft delete | `max_score` default 100.00; one of the eight soft-delete models. |

## Technical Notes

- `AssignmentViewSet` does not override `perform_create`, so `created_by` is taken from the payload rather than from `request.user`. Frontend convention is to send the tutor's own ID, but server enforcement is limited to the `IsTutor` role check.
- `Assignment.max_score` defaults to `100.00`; tutor-side grading (CU-07) does not enforce that submitted grades stay below `max_score`. Documenting this constraint is the tutor's responsibility.
- The Angular flow assumes one assignment per lesson — `LessonViewerComponent.loadAssignmentData` only takes `data[0]`. If multiple assignments are created for the same lesson via admin, the UI silently displays the first row only.
- The `?lesson=<id>` filter relies on the registered `filterset_fields` and `django_filter.DjangoFilterBackend` being the default filter backend (configured in `core_lms/settings.py`). Other filters (e.g., `?is_deleted=true`) are also supported but unused by the current SPA.
- The retry of failed assignments and the assignment lifecycle align with formative-assessment pedagogies that ground iteration on instructor-curated tasks; the platform does not currently surface AI-generated assignment scaffolding (Okonkwo et al., 2026).

## Request / Response

`GET /api/v1/assignments/?lesson=55` — HTTP 200

Response (paginated):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 14,
      "lesson": 55,
      "created_by": 3,
      "title": "Lab 2 - OOP Modeling",
      "description": "Upload UML and implementation files.",
      "due_date": "2026-05-05T23:59:00Z",
      "max_score": "100.00",
      "created_at": "2026-04-25T16:20:55.432120Z"
    }
  ]
}
```

`POST /api/v1/assignments/` — HTTP 201 (tutor-only)

Request:

```json
{
  "lesson": 55,
  "created_by": 3,
  "title": "Lab 2 - OOP Modeling",
  "description": "Upload UML and implementation files.",
  "due_date": "2026-05-05T23:59:00Z",
  "max_score": "100.00"
}
```

Response: same shape as the listing entry plus `id` and `created_at`.

`DELETE /api/v1/assignments/14/` — HTTP 204 (soft delete; `is_deleted=true` in the database).
