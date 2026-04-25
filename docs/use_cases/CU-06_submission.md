# CU-06 — Entregar asignación

## Overview

A student attaches a single file to an assignment from inside the lesson viewer; Angular wraps the file in `FormData` and sends it as `multipart/form-data` to Django's `SubmissionViewSet`. Django stores the binary in S3 under `submissions/{student_id}/{filename}` and inserts a `curriculum.Submission` row protected by `unique_together = (assignment, student)`. The same component then displays the submission status, grade, and the file URL once present.

## Actors and Preconditions

- Actor: Student.
- The caller is authenticated with `activeRole = 'STUDENT'` on the client and `request.user.role == 'STUDENT'` on the server.
- The lesson is loaded and contains an assignment (see CU-05).
- The student has not previously submitted for the same `(assignment, student)` pair — the unique constraint blocks duplicates.
- `sessionStore.userId()` is non-null; the component reads it to populate the `student` form field.

## Frontend Entry Point

- Route: `/student/course/:courseId` → `CourseViewerPageComponent` → sidebar lesson click → `<app-lesson-viewer />`.
- Component: `LessonViewerComponent` ([src/app/features/course/lesson-viewer/lesson-viewer.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/course/lesson-viewer/lesson-viewer.component.ts)).
- Trigger: file picker; the template binds `<input type="file" (change)="onFileSelected($event)" />`. The student selects a file and the change event fires `LessonViewerComponent.onFileSelected(event)` which immediately uploads.

## End-to-End Flow

1. Student selects a file. `onFileSelected(event)` reads `event.target.files[0]`; if absent, returns.
2. The component reads the loaded `assignment()` signal (populated by CU-05's lesson load) and `sessionStore.userId()`. If either is missing it bails with an error.
3. `isUploading.set(true)` and `uploadError.set(null)` to gate the UI.
4. `assignmentApi.submitAssignment(assignmentId, studentId, file)` ([src/app/entities/course/api/assignment.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/api/assignment.api.ts)) builds a `FormData` object with fields `assignment`, `student`, `file` (and a vestigial `status='PENDING'`), then calls `djangoApi.post<SubmissionItem>('/api/v1/submissions/', formData)`.
5. `DjangoApiClient.post` ([src/app/shared/api/django-api.client.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/api/django-api.client.ts)) forwards to `HttpClient`. Because the body is `FormData`, Angular omits the `Content-Type` header so the browser sets the correct `multipart/form-data; boundary=...` automatically.
6. `baseUrlInterceptor` prepends `environment.djangoApiUrl`; `authInterceptor` attaches `Authorization: Bearer ${accessToken}`.
7. Django routes the request via `apps/curriculum/urls.py` to `SubmissionViewSet.create` ([apps/curriculum/viewsets/submission_viewset.py](../../apps/curriculum/viewsets/submission_viewset.py)).
8. `get_permissions()` for the `create` action returns `[IsStudent()]`.
9. `SubmissionSerializer` validates `assignment`, `student`, `file` (the parser is `MultiPartParser`, configured globally).
10. On `serializer.save()` the `file` field is routed through `submission_upload_path(instance, filename)` ([apps/curriculum/services/storage_service.py](../../apps/curriculum/services/storage_service.py)), returning `submissions/{instance.student_id}/{filename}`.
11. `S3Boto3Storage` (configured in `core_lms/settings.py:183-192`) writes the binary; the `Submission` row is inserted with `submitted_at = now()`.
12. If a submission already exists for the same `(assignment, student)`, the database raises `IntegrityError`; DRF surfaces it as HTTP 400 (the standard validation envelope).
13. Django returns HTTP 201 with the serialized submission, including the public S3 URL in `file`.
14. The component awaits the promise; on success it calls `submission.set(response)` so the template switches from "upload" mode to "submitted" mode displaying the file link, `submitted_at`, and (after CU-07 grading) the grade.
15. On failure the component sets `uploadError.set(message)` and `isUploading.set(false)`; the file picker remains active for retry.

## Angular Implementation

- `AssignmentApiService.submitAssignment(assignmentId: number, studentId: number, file: File): Observable<SubmissionItem>`. Internals:

  ```ts
  const formData = new FormData();
  formData.append('assignment', String(assignmentId));
  formData.append('student', String(studentId));
  formData.append('file', file);
  formData.append('status', 'PENDING');
  return this.client.post<SubmissionItem>('/api/v1/submissions/', formData);
  ```

  The `status` field is a vestigial value — Django's `Submission` model does not have a `status` column and ignores it.
- Type: `SubmissionItem = { id, assignment, student, file, submitted_at, grade, status }` per [src/app/entities/course/model/assignment.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/model/assignment.types.ts).
- No store layer; the component holds local `signal<SubmissionItem | null>(null)`, `isUploading = signal(false)`, `uploadError = signal<string | null>(null)`.
- Subscription pattern: `await firstValueFrom(...)` inside `async onFileSelected(event)`. After resolution `submission.set(response)`.
- Form: there is no `FormGroup`; the component uses raw `<input type="file">` and binds `(change)`. Validators are not used — the only client-side check is "non-null file".
- `LessonViewerComponent.loadAssignmentData` (called from `ngOnChanges`) chains a second call `assignmentApi.getSubmissionsByAssignment(assignment.id)` that returns `SubmissionItem[]`; the component picks the first matching the current student so the UI shows the existing submission on revisit.
- Errors from the interceptor chain pass through `apiErrorInterceptor` (logging only); the component's `catch` block writes `uploadError.set(error?.message ?? 'Upload failed')`.

## Backend Implementation

- Endpoint: `POST /api/v1/submissions/` (DRF router prefix `submissions` in `apps/curriculum/urls.py`).
- Viewset: `SubmissionViewSet` (`ModelViewSet`) at [apps/curriculum/viewsets/submission_viewset.py](../../apps/curriculum/viewsets/submission_viewset.py).
- `get_permissions()`: `IsStudent` for `create`; `IsTutor` for `update / partial_update / destroy / grade`; `IsAuthenticated` for `list / retrieve`.
- `get_queryset()`: students see only their own submissions (`Submission.objects.filter(student=request.user)`); tutors see all rows.
- Serializer: `SubmissionSerializer` (`apps/curriculum/serializers/submission_serializer.py`) with fields `[id, assignment, student, file, submitted_at, grade, graded_at]`; read-only `[id, submitted_at, grade, graded_at]`.
- Storage helper: `submission_upload_path(instance, filename)` → `submissions/{instance.student_id}/{filename}` ([apps/curriculum/services/storage_service.py](../../apps/curriculum/services/storage_service.py)).
- Models touched: `curriculum.Assignment` (FK validation), `learning.LMSUser` (FK validation, role check), `curriculum.Submission` (write).
- Status codes: 201 on success, 400 on duplicate (uniqueness violation), 400 on missing required fields, 401 on missing JWT, 403 on non-student `create`.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `curriculum.Assignment` | Read | FK validation. |
| `learning.LMSUser` | Read | `student` FK validation; role check from `IsStudent`. |
| `curriculum.Submission` | Create | `unique_together = (assignment, student)`; `submitted_at` is auto_now_add; `file` stored at `submissions/{student_id}/{filename}`. One of the eight soft-delete models. |

## Technical Notes

- `Submission` has `submitted_at` (DateTimeField, `auto_now_add=True`) — there is no `is_submitted` flag (`is_submitted` exists only on `QuizAttempt`). The Angular type therefore exposes `submitted_at` as the canonical timestamp; the presence of a row implies submission.
- `SubmissionViewSet.create` does not force `student = request.user`; the field is taken from the payload. This means a malicious authenticated student could attempt to submit on behalf of another, but DRF would still reject it through the unique constraint or the assignment FK if the value mismatches expectations. Defense in depth (forcing `student = request.user.id` server-side) is a known hardening opportunity.
- Files are served as direct public S3 URLs because `STORAGES["default"]` configures `default_acl=None` and `querystring_auth=False`. The Angular template renders `submission.file` as a hyperlink; the bucket policy controls access.
- Re-uploads are not supported by this flow — the unique constraint blocks a second `POST` for the same pair. The Angular UI does not expose a "replace submission" affordance and there is no `PATCH` of the `file` field.
- `Submission` inherits `SoftDeleteMixin`, so `DELETE /api/v1/submissions/{id}/` flips `is_deleted=True` instead of issuing a real delete; the row therefore remains visible to forensics through `Submission.all_objects`.
- Iterative submission cycles support formative pedagogy by tying student work to instructor-graded artifacts — the AI-generated remediation pathway documented in CU-09 is a parallel feedback channel that does not replace this submission/grading loop (Okonkwo et al., 2026).

## Request / Response

`POST /api/v1/submissions/` — HTTP 201 (multipart/form-data)

Multipart fields:

| Field | Type | Notes |
|---|---|---|
| `assignment` | int | required FK |
| `student` | int | required FK; expected to match `request.user.id` |
| `file` | binary | required |
| `status` | string | sent by Angular as `'PENDING'` but ignored by Django (no `status` column) |

Response:

```json
{
  "id": 28,
  "assignment": 14,
  "student": 2,
  "file": "https://core-lms-bucket.s3.us-east-1.amazonaws.com/submissions/2/lab2.zip",
  "submitted_at": "2026-04-25T16:35:40.115900Z",
  "grade": null,
  "graded_at": null
}
```

Duplicate submission (HTTP 400):

```json
{ "non_field_errors": ["The fields assignment, student must make a unique set."] }
```
