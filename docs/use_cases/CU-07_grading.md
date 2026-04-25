# CU-07 — Gestionar entregas y calificar

## Overview

Tutors review every submission for an assignment from inside the tutor course viewer, type a numeric grade per submission, and persist it via a dedicated `PATCH /api/v1/submissions/{id}/grade/` action. Angular caches draft grades in a `Map` so multiple submissions can be edited side-by-side, then saves them one at a time. Django's `SubmissionViewSet.grade` parses the grade as `Decimal`, sets `graded_at = timezone.now()`, and returns the updated row. Students see the grade on their next visit to the lesson viewer (CU-06).

## Actors and Preconditions

- Actor: Tutor.
- The caller is authenticated with `activeRole = 'TUTOR'` on the client and `request.user.role == 'TUTOR'` on the server.
- The target submission exists and the tutor has navigated to the lesson it belongs to.
- The grade payload is parseable as a `Decimal`; non-numeric values return HTTP 400.

## Frontend Entry Point

- Route: `/tutor/course/:courseId` → `TutorCourseViewerPageComponent` ([src/app/pages/tutor/course-viewer-page/course-viewer-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/tutor/course-viewer-page/course-viewer-page.component.ts)) → sidebar lesson click → `<app-grading-panel [lesson]="selectedLesson()!" />`.
- Component: `GradingPanelComponent` ([src/app/features/tutor/grading-panel/grading-panel.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/tutor/grading-panel/grading-panel.component.ts)).
- Trigger: per-row "Save" button next to each submission. The button binds `(click)="saveGrade(submission)"`.

## End-to-End Flow

1. Tutor selects a lesson in the sidebar; `TutorCourseViewerPageComponent.selectLesson(lesson)` updates the local `selectedLesson` signal.
2. `GradingPanelComponent.ngOnChanges` resets `assignment.set(null)`, `submissions.set([])`, then calls `loadAssignmentAndSubmissions(lessonId)`.
3. The component calls `assignmentApi.getAssignmentsByLesson(lessonId)`; if non-empty, it stores the first assignment in `assignment.set(...)`.
4. It then calls `assignmentApi.getSubmissionsByAssignment(assignment.id)` and writes the array into `submissions.set([...])`. For each submission it pre-fills `draftGrades.set(submission.id, submission.grade ?? '')` so the input boxes start with the existing value.
5. Tutor types a value in the per-row `<input type="number">`; the `(input)` binding calls `setDraftGrade(submission.id, value)` writing to the `draftGrades` Map.
6. Tutor clicks "Save". `saveGrade(submission)` reads `draftGrades.get(submission.id)`, sets `isSubmitting.set(submission.id)` to render a spinner on that row, and dispatches the PATCH.
7. The component injects `DjangoApiClient` directly (not through an entity API service) and calls `client.patch<SubmissionItem>('/api/v1/submissions/${id}/grade/', { grade: draftValue })`.
8. `baseUrlInterceptor` resolves the URL; `authInterceptor` attaches `Authorization: Bearer ${accessToken}`.
9. Django routes `PATCH /api/v1/submissions/{id}/grade/` via `apps/curriculum/urls.py` to the `@action` method `SubmissionViewSet.grade` ([apps/curriculum/viewsets/submission_viewset.py](../../apps/curriculum/viewsets/submission_viewset.py) lines 139-174).
10. Action-level `permission_classes = [IsTutor]` enforces tutor-only access; `IsAuthenticated` from class-level guard runs first.
11. The action validates `request.data.get('grade')`; missing key returns HTTP 400 `{"detail": "grade is required."}`. Non-decimal value returns HTTP 400 `{"detail": "grade must be a decimal value."}`.
12. The action sets `submission.grade = Decimal(str(grade_value))`, `submission.graded_at = timezone.now()`, and persists with `submission.save(update_fields=['grade', 'graded_at'])`.
13. Django returns the updated submission via `SubmissionSerializer` (HTTP 200).
14. The Angular component awaits the response and patches the local array: it replaces the matching submission in `submissions()` with the server response, clears `isSubmitting.set(null)`, and the row re-renders with the persisted grade and timestamp.

## Angular Implementation

- `GradingPanelComponent` injects `AssignmentApiService` and `DjangoApiClient` directly (no `GradingService` exists).
- HTTP calls used: `assignmentApi.getAssignmentsByLesson()`, `assignmentApi.getSubmissionsByAssignment()`, and inline `client.patch<SubmissionItem, { grade: string }>('/api/v1/submissions/${id}/grade/', { grade })`.
- State signals: `assignment = signal<AssignmentItem | null>(null)`, `submissions = signal<SubmissionItem[]>([])`, `isLoading = signal(false)`, `isSubmitting = signal<number | null>(null)` (holds the in-flight submission id), and a plain instance `Map<number, string> draftGrades` for per-row form state.
- Helpers: `getDraftGrade(submissionId)` reads the Map; `setDraftGrade(submissionId, value)` writes; `downloadSubmission(url)` calls `window.open(url, '_blank')`.
- No reactive `FormGroup`; the per-row inputs are template-driven `<input [value]="getDraftGrade(s.id)" (input)="setDraftGrade(s.id, $event.target.value)">`.
- Subscription pattern: `await firstValueFrom(client.patch(...))` inside `async saveGrade(submission)`; on success the component patches `submissions()` via `signal.update(arr => arr.map(...))`.
- Error handling: try/catch sets a transient toast through `GlobalToastService` ([src/app/shared/lib/services/toast.service.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/lib/services/toast.service.ts)) and `isSubmitting.set(null)`. The `apiErrorInterceptor` logs to the console.

## Backend Implementation

- Endpoint: `PATCH /api/v1/submissions/{id}/grade/` (custom `@action`).
- Viewset: `SubmissionViewSet` at [apps/curriculum/viewsets/submission_viewset.py](../../apps/curriculum/viewsets/submission_viewset.py). The action signature is `@action(detail=True, methods=['patch'], permission_classes=[IsTutor])` → `grade(self, request, pk=None)`.
- `get_permissions()` already returns `[IsTutor()]` for `update / partial_update / destroy`, but the action declares its own `permission_classes` for explicit clarity.
- Validation:
  - `grade_value = request.data.get('grade')`; if `None` → `Response({'detail': 'grade is required.'}, status=400)`.
  - `try: Decimal(str(grade_value)) except InvalidOperation: → 400`.
- Service: none; the action mutates `submission.grade` and `submission.graded_at` directly.
- `submission.save(update_fields=['grade', 'graded_at'])`.
- Serializer: `SubmissionSerializer` is used for the response only.
- Models touched: `curriculum.Submission` (read by PK then update); `learning.LMSUser` (`IsTutor` reads `request.user.role`).
- Status codes: 200 on success, 400 on missing/invalid grade, 401 on missing JWT, 403 on non-tutor.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `curriculum.Submission` | Read | Loaded by PK from the role-aware queryset (tutors see all). |
| `curriculum.Submission` | Update | `grade` and `graded_at` only; `save(update_fields=...)`. |
| `learning.LMSUser` | Read | `IsTutor` reads `request.user.role`. |

## Technical Notes

- The grading action is intentionally separate from the generic `update / partial_update`; it isolates grading semantics in audit trails and lets the tutor edit grade independently of file replacement (which is not supported anyway).
- The action accepts any decimal-compatible value; bounds against `Assignment.max_score` are not enforced. A grade of `999.99` will persist successfully — this is a known constraint that the current UI compensates for by displaying "X / max_score" but does not validate.
- Once a grade is written, the student sees it via CU-06's lesson viewer, which renders `submission.grade` and `submission.graded_at` from the same `SubmissionSerializer` payload. There is no notification channel (email, push) — the student must revisit the lesson to discover the grade.
- The `draftGrades` Map persists across re-renders because it is an instance field, not a signal; switching lessons resets it implicitly because `ngOnChanges` re-runs `loadAssignmentAndSubmissions`, which clears `submissions()` and re-seeds the Map.
- Linking grading outcomes to AI-driven feedback for adaptive plans is intentionally out of scope here: the adaptive remediation pathway runs on quiz attempts (CU-09), not on assignment grades. This keeps RAG-driven feedback fully behind quiz scoring rather than mixing instructor judgment with LLM output (Okonkwo et al., 2026).
- `apiErrorInterceptor` does not raise UI toasts; the component is responsible for surfacing failures, currently through `GlobalToastService` once it is wired into the component (the Save error path uses it).

## Request / Response

`PATCH /api/v1/submissions/28/grade/` — HTTP 200

Request:

```json
{ "grade": "87.50" }
```

Response:

```json
{
  "id": 28,
  "assignment": 14,
  "student": 2,
  "file": "https://core-lms-bucket.s3.us-east-1.amazonaws.com/submissions/2/lab2.zip",
  "submitted_at": "2026-04-25T16:35:40.115900Z",
  "grade": "87.50",
  "graded_at": "2026-04-25T16:48:22.001204Z"
}
```

Validation errors (HTTP 400):

```json
{ "detail": "grade is required." }
```

```json
{ "detail": "grade must be a decimal value." }
```
