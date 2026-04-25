# CU-04 — Gestionar recursos de lección

## Overview

Tutors upload lesson resources (PDFs, videos, images, documents) and any authenticated user retrieves them inline through the lesson viewer. Angular renders a video player for `VIDEO` resources and a download grid for the rest, sourcing the file URL straight from the `Resource.file` field, which Django serializes as a direct public S3 URL because `querystring_auth=False` in `STORAGES["default"]`. Resource creation is multipart, attaches the file to the `lesson` FK, and stores the object under `resources/{course_id}/{filename}` via the storage helper.

## Actors and Preconditions

- Actors: Tutor (upload, update, delete), Student (read), any authenticated user (read).
- The caller is authenticated. Mutating actions require `IsTutor` server-side.
- The target lesson exists; on upload the FK is validated by `ResourceSerializer`.
- For viewing, the lesson detail (CU-03) has been loaded so `LessonItem.resources[]` is populated by `LessonDetailSerializer`.

## Frontend Entry Point

- Route: `/student/course/:courseId` → `CourseViewerPageComponent`, or `/tutor/course/:courseId` → `TutorCourseViewerPageComponent`. Both protected by `authGuard` + `roleGuard`.
- Component: `LessonViewerComponent` ([src/app/features/course/lesson-viewer/lesson-viewer.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/course/lesson-viewer/lesson-viewer.component.ts)).
- Trigger:
  - View — selecting a lesson in the course-viewer sidebar calls `selectLesson(lesson)`, which sets the local `selectedLesson` signal and re-renders `<app-lesson-viewer [lesson]="selectedLesson()!" />`. `LessonViewerComponent.ngOnChanges` runs `loadAssignmentData(lesson.id)` whenever the input changes.
  - Upload — there is no Angular UI to upload `Resource` rows in this codebase. `LessonViewerComponent` only uploads `Submission` files (CU-06). Resource creation happens through Django admin or direct REST calls. [verify: no resource-upload component found under `src/app/features/`].

## End-to-End Flow

1. Lesson selection in the course viewer sets `selectedLesson` and triggers `LessonViewerComponent.ngOnChanges`.
2. The component reads `lesson.resources` (already embedded by `LessonDetailSerializer` during CU-03 load) and computes:
   - `hasVideo` — true if any resource has `resource_type === 'VIDEO'`.
   - `mainVideo` — the first `VIDEO` resource.
   - `otherResources` — non-video resources for the download grid.
3. The template renders a video element (placeholder source binding) for `mainVideo` and a grid of `<a>` tags for `otherResources`, each pointing to `resource.file` (a direct S3 URL).
4. Clicking a tile invokes `downloadFile(url)` which calls `window.open(url, '_blank')`.
5. For programmatic resource creation (admin / direct API), Angular would `POST /api/v1/resources/` as `multipart/form-data` containing `lesson`, `uploaded_by`, `file`, `resource_type`, `title`. The `DjangoApiClient` does not currently expose a typed wrapper for this — the only entity client in `src/app/entities/course/` is `assignment.api.ts`, not `resource.api.ts` [verify: no `resource.api.ts` found].
6. Django routes `POST /api/v1/resources/` to `ResourceViewSet.create` ([apps/learning/viewsets/resource_viewset.py](../../apps/learning/viewsets/resource_viewset.py)).
7. `get_permissions()` returns `[IsTutor()]` for create.
8. `ResourceSerializer` validates the payload and the `lesson` FK. On `save()` the `FileField`'s `upload_to=resource_upload_path` ([apps/learning/services/storage_service.py](../../apps/learning/services/storage_service.py)) returns `resources/{instance.lesson.module.course_id}/{filename}`.
9. The `S3Boto3Storage` backend (configured in `core_lms/settings.py:183-192`) uploads the binary to the bucket; the row is inserted with `default_acl=None` and `file_overwrite=False`.
10. Django returns HTTP 201 with the serialized `Resource` including the resolved `file` URL.
11. On retrieval, `ResourceSerializer.file` is rendered as the public bucket URL (e.g. `https://core-lms-bucket.s3.us-east-1.amazonaws.com/resources/12/lecture.pdf`); access is granted by the bucket policy, not by per-object ACL or pre-signed query strings.

## Angular Implementation

- No dedicated `ResourceApiService` exists. `Resource` items reach the UI nested inside the course detail response via `LessonDetailSerializer`, and live in `LessonItem.resources` per [src/app/entities/course/model/course.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/course/model/course.types.ts).
- `ResourceItem` type fields: `id, lesson, uploaded_by, file, resource_type, title, created_at`. `resource_type` is the literal uppercase string returned by Django (`PDF`, `VIDEO`, `DOCUMENT`, `IMAGE`, `OTHER`).
- `LessonViewerComponent`:
  - `@Input({ required: true }) lesson!: LessonItem`.
  - Computed signals `hasVideo`, `mainVideo`, `otherResources` filter `lesson.resources` by `resource_type`.
  - `downloadFile(url: string): void` opens the URL in a new tab.
  - `OnChanges` hook resets local `assignment`, `submission`, and `uploadError` signals when `lesson` changes (the assignment side is covered in CU-06).
- The template renders a video player placeholder when `hasVideo()` is true (the `<video>` element binds `src` to `mainVideo()?.file`); other resources are rendered as cards with file extension icons.
- No store wraps resources — they are derived from `courseStore.selectedCourseDetail()` indirectly through the lesson input.

## Backend Implementation

- Endpoint: `/api/v1/resources/` (DRF router registration in `apps/learning/urls.py`) → `ResourceViewSet` (`apps/learning/viewsets/resource_viewset.py`), a `ModelViewSet`.
- Permissions: `get_permissions()` returns `[IsAuthenticated()]` for `list / retrieve` and `[IsTutor()]` for `create / update / partial_update / destroy`.
- Serializer: `ResourceSerializer` (`apps/learning/serializers/resource_serializer.py`) with fields `[id, lesson, uploaded_by, file, resource_type, title, created_at]`; read-only `[id, created_at]`.
- Storage helper: `resource_upload_path(instance, filename)` at `apps/learning/services/storage_service.py:4-14` → `resources/{instance.lesson.module.course_id}/{filename}`.
- Filterset: `lesson`, `resource_type`, `is_deleted`.
- Models touched: `learning.Lesson` (FK validation), `learning.LMSUser` (`uploaded_by` FK validation, optional), `learning.Resource` (write/read; soft-delete capable).
- Status codes: 200/201 on read/create, 204 on (soft) delete, 400 on missing FK or invalid `resource_type`, 403 when a non-tutor attempts a write.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `learning.Lesson` | Read | FK validation on resource create. |
| `learning.LMSUser` | Read | Optional `uploaded_by` FK. |
| `learning.Resource` | Create / Read / Update / Soft delete | One of the eight soft-delete models; `resource_type` choices `PDF / VIDEO / DOCUMENT / IMAGE / OTHER`. |

## Technical Notes

- `Resource.resource_type` is uppercase (`PDF`, `VIDEO`, `DOCUMENT`, `IMAGE`, `OTHER`) per [apps/learning/models/resource_model.py](../../apps/learning/models/resource_model.py:23-28); lowercase aliases such as `pdf` or `video` are rejected by the model. The Angular template comparisons therefore use uppercase strings.
- Files are served by direct public bucket URLs because `STORAGES["default"]` configures `default_acl=None`, `querystring_auth=False`, and `file_overwrite=False` in `core_lms/settings.py:183-192`. Pre-signed URLs are not used.
- `ResourceViewSet` does not override `perform_create`, so `uploaded_by` is whatever the client sends — there is no auto-binding to `request.user`. Audit traces of upload identity should not rely on this field alone.
- `LessonViewerComponent` does not download the file through Angular — `window.open(url)` lets the browser stream the asset directly from S3, bypassing Angular's `HttpClient` and the JWT bearer interceptor.
- Modality-aware resource selection is the responsibility of AxiomEngine's adaptive plan, which annotates each `PlanItem.resources[]` with a `resource_type` matched to the student's VARK profile (Alharbi et al., 2025); the resource ingestion flow itself does not perform any modality classification.

## Request / Response

`POST /api/v1/resources/` — HTTP 201 (multipart/form-data; tutor-only)

Request (multipart fields):

| Field | Type | Notes |
|---|---|---|
| `lesson` | int | required FK |
| `uploaded_by` | int | optional FK; not auto-set from `request.user` |
| `resource_type` | string | one of `PDF`, `VIDEO`, `DOCUMENT`, `IMAGE`, `OTHER` |
| `title` | string | optional, max 255 chars |
| `file` | binary | required |

Response:

```json
{
  "id": 90,
  "lesson": 55,
  "uploaded_by": 3,
  "file": "https://core-lms-bucket.s3.us-east-1.amazonaws.com/resources/12/lecture04.pdf",
  "resource_type": "PDF",
  "title": "Lecture 04 Notes",
  "created_at": "2026-04-25T16:03:30.901121Z"
}
```

`GET /api/v1/resources/90/` — HTTP 200 returns the same shape.

Resource consumption from the SPA is implicit: the lesson detail call `GET /api/v1/courses/{id}/` returns the embedded `resources[]` per lesson, and `LessonViewerComponent` reads `resource.file` directly without a separate API call.
