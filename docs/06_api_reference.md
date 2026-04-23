# 06 -- API Reference

> Every endpoint in this document maps to a concrete viewset action in
> the source. URLs are sourced from `core_lms/urls.py` and
> `apps/*/urls.py`; permissions, request bodies, and response shapes
> come from the viewset and serializer files cited inline.

## General Conventions

- **Base URL:** `/api/v1/` (mounted by `core_lms/urls.py:46-48`).
- **Authentication:** JWT Bearer in `Authorization: Bearer <access>`
  (`core_lms/settings.py:118-123`, `SIMPLE_JWT.AUTH_HEADER_TYPES =
  ("Bearer",)` on line 138), except where the viewset sets
  `permission_classes = [AllowAny]`.
- **Content-Type:** `application/json` by default; `multipart/form-data`
  for file uploads (resource, submission).
- **Pagination:** `rest_framework.pagination.PageNumberPagination`,
  `PAGE_SIZE=20` (`core_lms/settings.py:115-117`). List responses:

  ```json
  { "count": 142, "next": ".../?page=2", "previous": null, "results": [...] }
  ```

- **Default filter backend:** `django_filter.DjangoFilterBackend`
  (`core_lms/settings.py:124-126`). Endpoints that expose filters list
  them under "Filters". Soft-delete–aware endpoints accept
  `?is_deleted=true` or `?is_deleted=false`.
- **Error envelope:** DRF default `{"detail": "..."}` for standard
  errors; viewsets that return custom errors use
  `{"error": "<code>", "details": "..."}` (e.g. certificate,
  attempts, proctoring). Unhandled 500s pass through
  `core_lms.exception_handler.custom_exception_handler` as
  `{"detail": "An unexpected error occurred. Please try again later."}`.

---

## 1. Authentication

Both auth endpoints live in `apps/learning/viewsets/auth_viewset.py`;
routes are registered directly in `core_lms/urls.py:35-42`.

### POST `/api/v1/auth/token/` — obtain token pair

| Attribute | Value |
|-----------|-------|
| View | `RateLimitedTokenView` (`auth_viewset.py:11`) |
| Permission | `AllowAny` (inherited from SimpleJWT) |
| Rate limit | `@ratelimit(key="ip", rate="10/m", method="POST", block=False)` (`auth_viewset.py:35-37`); 429 when exceeded |

Request body:
```json
{ "username": "string", "password": "string" }
```

Response 200:
```json
{ "access": "eyJ...", "refresh": "eyJ..." }
```

Status codes: 200, 401 (bad credentials), 429 (rate limit).

### POST `/api/v1/auth/token/refresh/` — refresh access token

| Attribute | Value |
|-----------|-------|
| View | `TaggedTokenRefreshView` (`auth_viewset.py:58`) |
| Permission | `AllowAny` |

Request body:
```json
{ "refresh": "eyJ..." }
```

Response 200 (with rotation enabled — `core_lms/settings.py:136-137`):
```json
{ "access": "eyJ...", "refresh": "eyJ..." }
```

The old refresh token is blacklisted after rotation.

### Token lifetimes
- Access token: **30 minutes** (`core_lms/settings.py:134`).
- Refresh token: **7 days** (`core_lms/settings.py:135`).
- `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`.

---

## 2. Academic Ontology

All ontology viewsets are `ModelViewSet` and apply
`get_permissions()` that returns `[IsTutor()]` for mutations and
`[IsAuthenticated()]` for reads (pattern identical across every file
listed below).

| Resource | Prefix | ViewSet |
|----------|--------|---------|
| Career | `/api/v1/careers/` | `CareerViewSet` (`apps/learning/viewsets/career_viewset.py:11`) |
| Semester | `/api/v1/semesters/` | `SemesterViewSet` (`semester_viewset.py:11`) |
| Course | `/api/v1/courses/` | `CourseViewSet` (`course_viewset.py:12`) |
| Module | `/api/v1/modules/` | `ModuleViewSet` (`module_viewset.py:11`) |
| Lesson | `/api/v1/lessons/` | `LessonViewSet` (`lesson_viewset.py:11`) |

Standard CRUD URLs for each: `GET /` (list),
`POST /` (create, IsTutor), `GET /{id}/` (retrieve),
`PUT /{id}/` (update, IsTutor), `PATCH /{id}/` (partial_update,
IsTutor), `DELETE /{id}/` (destroy, IsTutor).

### 2.1 Careers

`CareerViewSet` uses `CareerSerializer` on list/create/update and
`CareerDetailSerializer` on retrieve
(`apps/learning/serializers/career_serializer.py:6, 19`).

**Filters:** `is_deleted` (`career_viewset.py:22`).

**Request / list response body (`CareerSerializer`):**
```json
{ "id": 1, "name": "...", "code": "...", "description": "...", "created_at": "..." }
```
`read_only_fields = ["id", "created_at"]`.

**Retrieve response (`CareerDetailSerializer`)** adds a `semesters`
method field returning a list serialized by `SemesterSerializer`
(`career_serializer.py:26-44`):
```json
{
  "id": 1, "name": "...", "code": "...", "description": "...",
  "created_at": "...",
  "semesters": [{ /* SemesterSerializer */ }]
}
```

### 2.2 Semesters

`SemesterSerializer` fields:
`["id", "career", "name", "number", "year", "period", "created_at"]`;
read-only: `["id", "created_at"]`
(`apps/learning/serializers/semester_serializer.py:14-24`).

**Filters:** `career`, `is_deleted` (`semester_viewset.py:24`).

`period` choices: `"I"`, `"II"`, `"SUMMER"`
(`apps/learning/models/semester_model.py:21-24`).

### 2.3 Courses

Two serializers (`course_viewset.get_serializer_class`):
- List/create/update: `CourseListSerializer` with fields
  `["id", "semester", "name", "code", "description", "created_at"]`
  (`course_serializer.py:8-18`).
- Retrieve: `CourseDetailSerializer` — embeds a nested `semester`
  (full `SemesterSerializer`) and a `modules` method field that
  recursively embeds lessons (via `LessonDetailSerializer`)
  (`course_serializer.py:21-65`).

**Filters:** `semester`, `semester__career`, `is_deleted`
(`course_viewset.py:26`).

`CourseViewSet.retrieve` applies `prefetch_related(
"modules__lessons__resources")` to avoid N+1
(`course_viewset.py:67-89`).

### 2.4 Modules

`ModuleSerializer` fields:
`["id", "course", "title", "description", "order"]`
(`module_serializer.py:14-16`).

**Filters:** `course`, `is_deleted` (`module_viewset.py:24`).

### 2.5 Lessons

Two serializers (`lesson_viewset.get_serializer_class`):
- List/create/update: `LessonSerializer` —
  `["id", "module", "title", "content", "order"]`
  (`lesson_serializer.py:14-16`).
- Retrieve: `LessonDetailSerializer` — adds `resources` method field
  that returns the nested `ResourceSerializer` list
  (`lesson_serializer.py:19-44`).

**Filters:** `module`, `is_deleted` (`lesson_viewset.py:23`).

---

## 3. Resources

### `/api/v1/resources/` — `ResourceViewSet` (`resource_viewset.py:11`)

CRUD via `ModelViewSet`; `IsAuthenticated` for reads, `IsTutor` for
writes (`resource_viewset.py:29-37`). Serializer:
`ResourceSerializer` with fields
`["id", "lesson", "uploaded_by", "file", "resource_type", "title",
"created_at"]` (`resource_serializer.py:14-25`).

**Filters:** `lesson`, `resource_type`, `is_deleted`
(`resource_viewset.py:27`).

**POST request (multipart/form-data):**

| field | type | notes |
|-------|------|-------|
| `lesson` | int | required; FK to Lesson |
| `uploaded_by` | int | optional; usually set server-side from auth user |
| `file` | file | required |
| `resource_type` | string | one of `PDF`, `VIDEO`, `DOCUMENT`, `IMAGE`, `OTHER` (`resource_model.py:23-28`) |
| `title` | string | optional, max 255 |

**Response (example):**
```json
{
  "id": 1, "lesson": 3, "uploaded_by": 2,
  "file": "https://core-lms-bucket.s3.us-east-1.amazonaws.com/resources/5/lecture.pdf",
  "resource_type": "PDF",
  "title": "Chapter 1 Slides",
  "created_at": "2026-04-16T12:00:00Z"
}
```

`file` is rendered as a direct public URL via `AWS_S3_CUSTOM_DOMAIN`
(`core_lms/settings.py:171`). Stored S3 key follows
`resources/{course_id}/{filename}`
(`apps/learning/services/storage_service.py:4-14`).

---

## 4. Assignments

### `/api/v1/assignments/` — `AssignmentViewSet` (`apps/curriculum/viewsets/assignment_viewset.py:11`)

CRUD via `ModelViewSet`; `IsAuthenticated` for reads, `IsTutor` for
writes (`assignment_viewset.py:27-35`).
Serializer: `AssignmentSerializer`
(`apps/curriculum/serializers/assignment_serializer.py:6`) with fields
`["id", "lesson", "created_by", "title", "description", "due_date",
"max_score", "created_at"]`; read-only `["id", "created_at"]`.

**Filters:** `lesson`, `created_by`, `is_deleted`
(`assignment_viewset.py:25`).

**Request body (POST):**
```json
{
  "lesson": 1,
  "title": "Lab Exercise 1",
  "description": "...",
  "due_date": "2026-05-01T23:59:00Z",
  "max_score": "100.00"
}
```

---

## 5. Submissions

### `/api/v1/submissions/` — `SubmissionViewSet` (`apps/curriculum/viewsets/submission_viewset.py:15`)

ModelViewSet with dynamic permissions and queryset scoping:

- `get_queryset` scopes to `student=request.user` when caller is a
  student, returns all rows for tutors
  (`submission_viewset.py:31-47`).
- `get_permissions`: `create` requires `IsStudent`;
  `update`/`partial_update`/`destroy`/`grade` require `IsTutor`;
  `list`/`retrieve` require `IsAuthenticated`
  (`submission_viewset.py:49-61`).

Serializer: `SubmissionSerializer`
(`apps/curriculum/serializers/submission_serializer.py:6`) with fields
`["id", "assignment", "student", "file", "submitted_at", "grade",
"graded_at"]`; read-only
`["id", "submitted_at", "grade", "graded_at"]`.

**Filters:** `assignment`, `is_deleted` (`submission_viewset.py`).

**POST (multipart/form-data):**

| field | type | notes |
|-------|------|-------|
| `assignment` | int | required |
| `student` | int | required (matches authenticated student) |
| `file` | file | required |

Unique constraint `(assignment, student)` — second POST returns 400 /
integrity error.

### PATCH `/api/v1/submissions/{id}/grade/` — `SubmissionViewSet.grade`

`@action(detail=True, methods=["patch"], permission_classes=[IsTutor])`
(`submission_viewset.py:139`).

Request:
```json
{ "grade": "85.50" }
```

Response: the updated submission via `SubmissionSerializer` with
`grade` and `graded_at` populated. 400 if `grade` is missing or cannot
be parsed as a Decimal.

---

## 6. Quizzes

### `/api/v1/quizzes/` — `QuizViewSet` (`apps/assessments/viewsets/quiz_viewset.py:9`)

**Read-only** (`ReadOnlyModelViewSet`);
`permission_classes = [AllowAny]` (`quiz_viewset.py:10-19`).
`queryset = Quiz.objects.filter(is_active=True)`.

- `list` uses `QuizListSerializer` — fields `["id", "title", "course",
  "time_limit_minutes", "is_active", "question_count"]`, where
  `question_count` is a `SerializerMethodField`
  (`apps/assessments/serializers/quiz_serializer.py:29-35`).
- `retrieve` uses `QuizDetailSerializer` — fields `["id", "title",
  "description", "course", "time_limit_minutes", "is_active",
  "questions"]`
  (`apps/assessments/serializers/quiz_serializer.py:37-43`).
  `questions[]` embeds `QuestionSerializer` with fields
  `["id", "text", "concept_id", "order", "choices"]`
  (`quiz_serializer.py:21-27`); `choices[]` embeds
  `AnswerChoiceSerializer` with fields **`["id", "text"]` only** — no
  `is_correct` (`quiz_serializer.py:6-11`).

Example retrieve response:
```json
{
  "id": 1, "course": 1,
  "title": "Midterm Exam", "description": "...",
  "time_limit_minutes": 30, "is_active": true,
  "questions": [
    { "id": 1, "text": "...", "concept_id": "Variables", "order": 1,
      "choices": [{ "id": 1, "text": "..." }, { "id": 2, "text": "..." }] }
  ]
}
```

---

## 7. Attempts

### `/api/v1/attempts/` — `AttemptViewSet` (`apps/assessments/viewsets/attempt_viewset.py:101`)

Viewset type: `viewsets.ViewSet` (no automatic CRUD). Permissions:
`[IsAuthenticated, IsStudent]` (line 115).

#### POST `/api/v1/attempts/` — `create`

Body validated by `AttemptSubmitSerializer`
(`apps/assessments/serializers/attempt_serializer.py:11-18`):
```json
{
  "quiz_id": 1,
  "student_id": 2,
  "answers": [
    { "question_id": 1, "selected_choice_id": 3 },
    { "question_id": 2, "selected_choice_id": 7 }
  ]
}
```

Behaviour (`attempt_viewset.py:139-186`):
1. 400 if student or quiz not found.
2. Creates `QuizAttempt` and bulk-inserts `AttemptAnswer` rows.
3. `ScoringService.score_and_evaluate(attempt)` computes score,
   creates Evaluation / FailedTopic / EvaluationTelemetry, and stores
   `adaptive_plan` on the attempt (see 02_use_cases.md § UC-01 for the
   service call chain).
4. Response (201) merges `AttemptResultSerializer(attempt).data` with
   the service result dict:

```json
{
  "id": 42, "student": 2, "quiz": 1,
  "start_time": "...", "end_time": "...",
  "final_score": "3.00", "is_submitted": true,
  "adaptive_plan": { /* union -- see 04_architecture § 3.1 */ },
  "score": 3.0, "max_score": 4.0,
  "failed_concepts": ["Polymorphism"],
  "evaluation_id": 17
}
```

Note the heterogeneous `adaptive_plan` envelope (§ 04 CV-02).

#### GET `/api/v1/attempts/` — `list`

Returns paginated `AttemptResultSerializer` results filtered to
`student=request.user`
(`apps/assessments/viewsets/attempt_viewset.py:197-215`).

#### GET `/api/v1/attempts/{id}/` — `retrieve`

Row-level scoped: returns 404 if `pk` belongs to another student
(`apps/assessments/viewsets/attempt_viewset.py:232-250`).

---

## 8. Proctoring

### POST `/api/v1/proctoring/logs/` — `ProctoringViewSet.create` (`apps/assessments/viewsets/proctoring_viewset.py:100`)

Permission: `[IsAuthenticated, IsStudent]`
(`proctoring_viewset.py:81`).

Request body validated by `ProctoringBulkSerializer`
(`apps/assessments/serializers/proctoring_serializer.py:13-18`):
```json
{
  "events": [
    { "attempt": 42, "event_type": "tab_switched",
      "timestamp": "2026-04-16T14:10:23Z", "severity_score": "0.80" },
    { "attempt": 42, "event_type": "face_not_detected",
      "timestamp": "2026-04-16T14:12:05Z", "severity_score": "0.95" }
  ]
}
```

`event_type` choices (exactly three; `apps/assessments/models/proctoring_model.py:10-13`):
- `"tab_switched"`
- `"face_not_detected"`
- `"multiple_faces"`

Response 201:
```json
{ "ingested": 2 }
```

---

## 9. Analytics

### GET `/api/v1/analytics/course/{course_id}/dashboard/` — `TeacherDashboardViewSet.course_dashboard` (`apps/assessments/viewsets/analytics_viewset.py:131-224`)

Permission: `[IsAuthenticated, IsTutor]`
(`analytics_viewset.py:96`). Path param `course_id` must be a
positive integer (`url_path=r"course/(?P<course_id>[^/.]+)/dashboard"`).

Response 200 (`analytics_viewset.py:215-224`):
```json
{
  "course_id": 1,
  "course_code": "CS-201",
  "course_name": "Advanced Programming",
  "total_enrolled_students": 10,
  "average_quiz_score": 72.50,
  "proctoring_alerts": { "tab_switched": 6, "multiple_faces": 4 },
  "vark_distribution": { "visual": 3, "aural": 2, "read_write": 3, "kinesthetic": 2 },
  "top_failed_concepts": [
    { "concept_id": "Polymorphism", "fail_count": 3 },
    { "concept_id": "Recursion", "fail_count": 2 }
  ]
}
```

> `proctoring_alerts` includes only events in `CRITICAL_EVENT_TYPES =
> [TAB_SWITCHED, MULTIPLE_FACES]` (`analytics_viewset.py:98-101`).
> `face_not_detected` is **deliberately excluded** from this aggregate.

Response 404: course not found — `{"error": "not_found", "detail":
"Course not found."}`.

---

## 10. Certificates

### POST `/api/v1/certificates/generate/` — `CertificateViewSet.generate` (`apps/learning/viewsets/certificate_viewset.py:77-129`)

Permission: `[IsAuthenticated, IsStudent]`
(`certificate_viewset.py:22`).

Request:
```json
{ "student_id": 2, "course_id": 1 }
```

Response 201:
```json
{
  "certificate_hash": "a3f8c2e1...",  // 64-char SHA-256 hex digest
  "issued_at":        "2026-04-16T15:00:00Z",
  "course_id": 1,
  "student_id": 2
}
```

Status codes:
| Code | Meaning | Source |
|------|---------|--------|
| 201  | certificate issued (or existing one returned idempotently) | `certification_service.py:94-123` |
| 400  | missing student_id/course_id, or student/course not found | `certificate_viewset.py:90-110` |
| 403  | no passing Evaluation (`score >= 60.00`) and no passing QuizAttempt (`final_score >= 60.00`) — `{"error": "ineligible", "detail": "..."}` | `certificate_viewset.py:115-119`; `certification_service.py:52-73` |

---

## 11. Users

### POST `/api/v1/users/{id}/onboard/` — `UserViewSet.onboard` (`apps/learning/viewsets/user_onboarding_viewset.py:117`)

Permission: `[IsAuthenticated]` (line 95). Returns 403 if the caller is
not the same user as `id` (line 130-134).

Request body (`VARKOnboardingSerializer`, lines 13-21):
```json
{
  "answers": [
    { "category": "visual", "value": 7 },
    { "category": "aural", "value": 3 },
    { "category": "read_write", "value": 5 },
    { "category": "kinesthetic", "value": 4 }
  ]
}
```

- `category` must be one of `"visual"`, `"aural"`, `"read_write"`,
  `"kinesthetic"`.
- `value` must be an integer 0-10.

Response 200 (`user_onboarding_viewset.py:153-160`):
```json
{
  "student_id": 2,
  "vark_scores": { "visual": 7, "aural": 3, "read_write": 5, "kinesthetic": 4 },
  "vark_dominant": "visual"
}
```

The dominant modality is persisted to `user.vark_dominant`
(line 150-151). Values are exactly as listed; in particular the service
uses `"aural"` (not `"auditory"`), which differs from the Go
`vark_profile` documentation — see `04_architecture.md` § 5 CV-01.

---

## 12. Evaluations

### `/api/v1/evaluations/` — `EvaluationViewSet` (`apps/learning/viewsets/evaluation_viewset.py:15`)

ModelViewSet; all actions require `IsAuthenticated` only
(`evaluation_viewset.py:26`). Serializer: `EvaluationSerializer`
(`apps/learning/serializers/evaluation_serializer.py:8`).

Serializer fields (lines 18-29):
`["id", "student", "course", "score", "max_score", "created_at",
"failed_topics", "telemetry"]`; read-only `["id", "created_at"]`.

`failed_topics` — list of `FailedTopicSerializer`
(`failed_topic_serializer.py:6-10`) with
`["id", "concept_id", "score", "max_score"]`.
`telemetry` — nested `TelemetrySerializer`
(`telemetry_serializer.py:6-9`) with
`["time_on_task_seconds", "clicks"]`, `required=False`.

#### POST `/api/v1/evaluations/` — `create` (`evaluation_viewset.py:42-80`)

Request:
```json
{
  "student": 2, "course": 1,
  "score": "85.50", "max_score": "100.00",
  "failed_topics": [
    { "concept_id": "Recursion", "score": "2.00", "max_score": "5.00" }
  ],
  "telemetry": { "time_on_task_seconds": 1800, "clicks": 120 }
}
```

Response 201 — the serialized evaluation with two added keys:

- `adaptive_plan` — `PlanResponse` from Go, or `null` if no
  `failed_topics`. Present whenever the pipeline runs.
- `axiom_error` — present only when Go returned an error (timeout or
  non-2xx); structure:
  ```json
  { "error": "axiom_timeout|axiom_error", "status_code": 500, "details": "..." }
  ```
  (`evaluation_viewset.py:64-78`). **Unlike the scoring path, this
  endpoint does not substitute a `{"plan":[],"fallback":true}`
  envelope on error.**

Other CRUD methods (`list`, `retrieve`, `update`, `partial_update`,
`destroy`) are standard DRF implementations over the same serializer.

---

## 13. Evaluation Telemetry

### `/api/v1/evaluation-telemetry/` — `EvaluationTelemetryViewSet` (`apps/assessments/viewsets/evaluation_telemetry_viewset.py:16`)

ModelViewSet over `EvaluationTelemetry`. Serializer:
`EvaluationTelemetrySerializer`
(`apps/assessments/serializers/telemetry_serializer.py:8`) with fields
`["id", "evaluation", "time_on_task_seconds", "clicks"]`; read-only
`["id"]`.

Dynamic permissions (`evaluation_telemetry_viewset.py:45-55`):
- `create` → `[IsStudent]`
- `list`, `retrieve` → `[IsAuthenticated]`
- others (`update`, `partial_update`, `destroy`) → `[IsTutor]`

Row-level queryset scoping
(`evaluation_telemetry_viewset.py:29-43`): students see only their own
telemetry (via `evaluation.student=self.request.user`); tutors see all.

---

## 14. System

### GET `/health/` — `health_check` (`apps/learning/viewsets/health_viewset.py:14-18`)

`@api_view(["GET"])`, `@permission_classes([AllowAny])`. Registered at
`core_lms/urls.py:31`. Returns:
```json
{ "status": "ok" }
```

### `/swagger/` and `/redoc/`

API documentation UIs backed by `drf_yasg`
(`core_lms/urls.py:51-60`). `AllowAny`.

### `/admin/` — Django admin (`core_lms/urls.py:28`).

---

## Appendix A: Permission classes

| Class | Source | Check |
|-------|--------|-------|
| `AllowAny` | DRF | always true |
| `IsAuthenticated` | DRF | request.user.is_authenticated |
| `IsStudent` | `apps/learning/permissions.py:4-18` | authenticated AND `request.user.role == "STUDENT"` |
| `IsTutor` | `apps/learning/permissions.py:21-35` | authenticated AND `request.user.role == "TUTOR"` |

> Role values are uppercase (`"STUDENT"`, `"TUTOR"`) as defined by
> `LMSUser.Role` (`apps/learning/models/user_model.py:13-15`).

---

## Appendix B: Common query parameters

| Parameter | Where applicable | Description |
|-----------|------------------|-------------|
| `page` | all list endpoints | page number for `PageNumberPagination` |
| `is_deleted` | career, semester, course, module, lesson, resource, assignment, submission | filter soft-deleted rows; default manager already excludes `is_deleted=True` |
| `career` | semester | filter semesters by career id |
| `semester`, `semester__career` | course | filter by semester / parent career |
| `course` | module, quiz | filter by course id |
| `module` | lesson | filter by module id |
| `lesson`, `resource_type` | resource | filter resources |
| `lesson`, `created_by` | assignment | filter assignments |
| `assignment` | submission | filter submissions |

---

## Appendix C: HTTP status codes in use

| Code | Meaning | Notable sources |
|------|---------|-----------------|
| 200 | GET/PUT/PATCH success | all list/retrieve |
| 201 | resource created | all POST |
| 204 | deleted | soft-delete DELETE |
| 400 | validation error; custom 400 in attempts/certificate/analytics on missing FK | various |
| 401 | missing/invalid JWT | DRF `IsAuthenticated` |
| 403 | wrong role or ineligible student | `IsStudent`, `IsTutor`, certificate ineligibility |
| 404 | not found (incl. row-level scoping miss) | retrieve actions |
| 429 | rate limit | `RateLimitedTokenView`; AxiomEngine (Go side) |
| 500 | unhandled exception | replaced with JSON envelope via `core_lms.exception_handler` |

---

## Appendix D: Frontend integration notes

### Auth flow
1. `POST /api/v1/auth/token/` → store `access` and `refresh` in memory.
2. Add `Authorization: Bearer <access>` to every request.
3. On 401, `POST /api/v1/auth/token/refresh/` with `{refresh}`; the
   response **replaces** both tokens (old refresh is blacklisted).
4. On 401 from the refresh endpoint, redirect to login.

### File URLs
The `file` field rendered in responses is a direct public S3 URL (e.g.
`https://core-lms-bucket.s3.us-east-1.amazonaws.com/submissions/2/file.pdf`).
Access is controlled by the S3 bucket policy, not per-object ACLs or
pre-signed URLs.

### Heterogeneous `adaptive_plan`
When consuming `/api/v1/attempts/`, branch on the presence of
`fallback`:
- **Success** — `adaptive_plan.student_id`, `adaptive_plan.course_id`,
  `adaptive_plan.items[]`, `adaptive_plan._meta` (see § 04 for field
  list).
- **Fallback** — `adaptive_plan.plan === []` and
  `adaptive_plan.fallback === true`. Display a neutral message.

### Direct call to AxiomEngine
The cognitive-shadow-graph endpoint
`GET /api/v1/tutor/student/:student_id/cognitive-graph?topics=...`
lives on **the Go service**, not Django. Route it to
`AXIOM_ENGINE_URL` directly. See `04_architecture.md` § 3.2.
