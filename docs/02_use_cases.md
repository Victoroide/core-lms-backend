# 02 -- Use Cases

> Every use case maps to one or more concrete ViewSet actions or Go
> handler functions. If an endpoint is not listed here, there is no
> server-side implementation. See `Coverage Notes` at the end for
> intentionally absent features.

---

## UC-01: Obtain JWT Access Token (Login)

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-01 |
| **Actor**       | Any user (unauthenticated) |
| **Endpoint**    | `POST /api/v1/auth/token/` → `RateLimitedTokenView.post` (`apps/learning/viewsets/auth_viewset.py:38`) |
| **Permissions** | None (unauthenticated) |

### Preconditions
- A valid `LMSUser` account exists with the submitted credentials.

### Main Flow
1. Client POSTs `{"username": "...", "password": "..."}`.
2. `@ratelimit(key="ip", rate="10/m", method="POST", block=False)` is
   evaluated first (`apps/learning/viewsets/auth_viewset.py:35-36`). If
   `request.limited` is `True`, returns 429 with
   `{"detail": "Too many login attempts. Try again later."}` (lines 50-54).
3. Otherwise, delegates to SimpleJWT `TokenObtainPairView.post`, which
   validates credentials and returns a token pair.
4. Access token lifetime: `timedelta(minutes=30)`
   (`core_lms/settings.py:134`).
   Refresh token lifetime: `timedelta(days=7)`
   (`core_lms/settings.py:135`).

### Response shape (200)
```json
{
  "access":  "<JWT access token>",
  "refresh": "<JWT refresh token>"
}
```

### Exceptions
- **401** — invalid credentials (SimpleJWT default).
- **429** — IP rate limit (10/min) exceeded.

---

## UC-02: Rotate Refresh Token

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-02 |
| **Actor**       | Any user holding a valid refresh token |
| **Endpoint**    | `POST /api/v1/auth/token/refresh/` → `TaggedTokenRefreshView.post` (`apps/learning/viewsets/auth_viewset.py:74`) |
| **Permissions** | None (unauthenticated route, validated by token) |

### Main Flow
1. Client POSTs `{"refresh": "<refresh token>"}`.
2. SimpleJWT `TokenRefreshView` validates the token, checks the blacklist,
   and issues a new access + refresh pair.
3. `ROTATE_REFRESH_TOKENS = True` and `BLACKLIST_AFTER_ROTATION = True`
   (`core_lms/settings.py:136-138`) are set, so the submitted refresh
   token is immediately blacklisted after rotation.

### Response shape (200)
```json
{
  "access":  "<new JWT access token>",
  "refresh": "<new JWT refresh token>"
}
```

### Exceptions
- **401** — token invalid, expired, or already blacklisted.

---

## UC-03: Student Completes VARK Onboarding

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-03 |
| **Actor**       | Student |
| **Endpoint**    | `POST /api/v1/users/{id}/onboard/` → `UserViewSet.onboard` (`apps/learning/viewsets/user_onboarding_viewset.py:117`) |
| **Permissions** | `[IsAuthenticated]` (`apps/learning/viewsets/user_onboarding_viewset.py:95`) |

### Preconditions
- User must be authenticated and the `{id}` path parameter must match
  `request.user.pk`.

### Main Flow
1. Client POSTs body validated by `VARKOnboardingSerializer`
   (`apps/learning/viewsets/user_onboarding_viewset.py:13-21`):
   ```json
   {
     "answers": [
       {"category": "visual|aural|read_write|kinesthetic", "value": 0}
     ]
   }
   ```
   where `value` is an integer 0–10 and `category` must be one of the
   four VARK modalities
   (`apps/learning/models/user_model.py:17-21`).
2. Returns 403 if `user.pk != request.user.pk`
   (`apps/learning/viewsets/user_onboarding_viewset.py:130-134`).
3. Sums `value` per `category`; the modality with the highest sum becomes
   `vark_dominant` (lines 139-149).
4. Persists `user.vark_dominant` (lines 150-151).

### Response shape (200)
```json
{
  "student_id":   2,
  "vark_scores":  {"visual": 7, "aural": 3, "read_write": 5, "kinesthetic": 4},
  "vark_dominant": "visual"
}
```
(`apps/learning/viewsets/user_onboarding_viewset.py:153-160`)

### Exceptions
- **400** — missing or invalid `answers` payload.
- **403** — caller's PK does not match the path `{id}`.

---

## UC-04: Authenticated User Browses Academic Ontology

Any authenticated user may retrieve the full ontology hierarchy in
read-only mode. All resources use `ModelViewSet` with `[IsAuthenticated]`
on safe methods and `[IsTutor]` on mutating methods (see UC-05).

| Resource    | Endpoint prefix        | ViewSet              | Source |
|-------------|------------------------|----------------------|--------|
| Career      | `/api/v1/careers/`     | `CareerViewSet`      | `apps/learning/viewsets/career_viewset.py:11` |
| Semester    | `/api/v1/semesters/`   | `SemesterViewSet`    | `apps/learning/viewsets/semester_viewset.py:11` |
| Course      | `/api/v1/courses/`     | `CourseViewSet`      | `apps/learning/viewsets/course_viewset.py:12` |
| Module      | `/api/v1/modules/`     | `ModuleViewSet`      | `apps/learning/viewsets/module_viewset.py:11` |
| Lesson      | `/api/v1/lessons/`     | `LessonViewSet`      | `apps/learning/viewsets/lesson_viewset.py:11` |
| Resource    | `/api/v1/resources/`   | `ResourceViewSet`    | `apps/learning/viewsets/resource_viewset.py:11` |

Detail-view serializers return nested hierarchies:
`CareerDetailSerializer` embeds `semesters`
(`apps/learning/serializers/career_serializer.py:19`);
`CourseDetailSerializer` embeds modules with lessons
(`apps/learning/serializers/course_serializer.py:21-65`);
`LessonDetailSerializer` embeds resources
(`apps/learning/serializers/lesson_serializer.py:19-44`).

Soft-deleted objects (`is_deleted=True`) are excluded by the default
manager; use `?is_deleted=true` filter to include them (on viewsets that
expose `filterset_fields = ["is_deleted"]`).

---

## UC-05: Tutor Manages Academic Hierarchy (Write CRUD)

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-05 |
| **Actor**       | Tutor |
| **Endpoints**   | `POST/PUT/PATCH/DELETE` on any ontology prefix (see UC-04 table) |
| **Permissions** | `[IsTutor]` on `create`, `update`, `partial_update`, `destroy` |

### Main Flow
1. Tutor submits a mutating request. The `get_permissions()` override on
   each ViewSet returns `[IsTutor()]` for write actions and
   `[IsAuthenticated()]` for read actions.
2. On `destroy`, soft-delete models set `is_deleted=True`; a SQL
   `DELETE` is never issued
   (`apps/learning/models/mixins.py` — `SoftDeleteMixin.delete()`).
3. `SoftDeleteManager` automatically hides soft-deleted rows from
   all subsequent queries.

### Eight soft-deletable models
`Career`, `Semester`, `Course`, `Module`, `Lesson`, `Resource`,
`Assignment`, `Submission`
(`apps/learning/models/mixins.py`, `apps/curriculum/models/`).

---

## UC-06: Tutor Uploads Lesson Resource

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-06 |
| **Actor**       | Tutor |
| **Endpoint**    | `POST /api/v1/resources/` (multipart) → `ResourceViewSet.create` (`apps/learning/viewsets/resource_viewset.py:80`) |
| **Permissions** | `[IsTutor]` (`apps/learning/viewsets/resource_viewset.py:35`) |

### Main Flow
1. Tutor POSTs `multipart/form-data` containing `lesson` (FK), `title`,
   `resource_type`, `file`.
2. `ResourceSerializer` validates and calls `.save()`. The `file` field
   is routed through the S3 default storage backend
   (`core_lms/settings.py:171-180`). Upload path is computed by
   `resource_upload_path(instance, filename)` →
   `f"resources/{instance.lesson.module.course_id}/{filename}"`
   (`apps/learning/services/storage_service.py:4-14`).
3. S3 backend config: `default_acl="private"`, `querystring_auth=True`,
   `querystring_expire=3600` (`core_lms/settings.py:176-179`).
4. Returns 201 with the serialized `Resource` including a pre-signed URL
   for the uploaded file.

---

## UC-07: Authenticated User Downloads Resource

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-07 |
| **Actor**       | Any authenticated user |
| **Endpoint**    | `GET /api/v1/resources/{id}/` → `ResourceViewSet.retrieve` (`apps/learning/viewsets/resource_viewset.py:62`) |
| **Permissions** | `[IsAuthenticated]` |

### Main Flow
1. Client GETs the resource URL.
2. `ResourceSerializer` serializes the `file` field. Because
   `querystring_auth=True`, the `S3Boto3Storage` backend generates a
   pre-signed URL valid for 3 600 seconds (1 hour)
   (`core_lms/settings.py:178-179`).
3. Client follows the pre-signed URL directly to S3 to download the file.

### Exceptions
- **404** — resource not found or `is_deleted=True`.

---

## UC-08: Tutor Manages Assignments

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-08 |
| **Actor**       | Tutor |
| **Endpoint**    | `POST/GET/PUT/PATCH/DELETE /api/v1/assignments/` → `AssignmentViewSet` (`apps/curriculum/viewsets/assignment_viewset.py:11`) |
| **Permissions** | `[IsTutor]` for writes; `[IsAuthenticated]` for reads |

### Main Flow
1. Tutor CRUDs assignment records linked to a `Lesson` via FK.
2. `AssignmentSerializer` exposes `lesson`, `title`, `description`,
   `due_date`, `max_grade` fields.
3. Soft-delete on `destroy` — `is_deleted=True`; row is hidden from
   default queryset.

---

## UC-09: Student Submits File-Based Assignment

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-09 |
| **Actor**       | Student |
| **Endpoint**    | `POST /api/v1/submissions/` (multipart) → `SubmissionViewSet.create` (`apps/curriculum/viewsets/submission_viewset.py`) |
| **Permissions** | `[IsStudent]` (`apps/curriculum/viewsets/submission_viewset.py:55`) |

### Main Flow
1. Student POSTs `multipart/form-data` with `assignment` (FK) and `file`.
2. File is stored under `submissions/{instance.student_id}/{filename}` by
   `submission_upload_path`
   (`apps/curriculum/services/storage_service.py:4-14`).
3. `unique_together = [("assignment", "student")]` on `Submission`
   (`apps/curriculum/models/submission_model.py:46`) enforces at most one
   submission per student per assignment. A duplicate POST returns 400
   via `IntegrityError` surfaced by DRF.

---

## UC-10: User Views Submissions (Row-Level Scoping)

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-10 |
| **Actor**       | Student or Tutor |
| **Endpoint**    | `GET /api/v1/submissions/` and `GET /api/v1/submissions/{id}/` → `SubmissionViewSet` (`apps/curriculum/viewsets/submission_viewset.py:31-47`) |
| **Permissions** | `[IsAuthenticated]` |

### Main Flow
1. `get_queryset()` checks `request.user.role`:
   - `STUDENT` → filter `student=request.user`.
   - Any other role → all submissions.
2. Optional filter `?assignment=<id>` via `filterset_fields = ["assignment",
   "is_deleted"]` (`apps/curriculum/viewsets/submission_viewset.py:29`).

---

## UC-11: Tutor Grades a Submission

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-11 |
| **Actor**       | Tutor |
| **Endpoint**    | `PATCH /api/v1/submissions/{id}/grade/` → `SubmissionViewSet.grade` (`apps/curriculum/viewsets/submission_viewset.py:139-174`) |
| **Permissions** | `[IsTutor]` (`apps/curriculum/viewsets/submission_viewset.py:59-60`) |

### Main Flow
1. Tutor PATCHes `{"grade": "<decimal>"}`.
2. Action validates `grade` is a parseable `Decimal`; returns 400 if
   missing or invalid.
3. Sets `submission.grade` and `submission.graded_at = timezone.now()`.
4. Returns the updated `Submission` via `SubmissionSerializer`.

---

## UC-12: Browse Quizzes (Public)

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-12 |
| **Actor**       | Any user (unauthenticated allowed) |
| **Endpoints**   | `GET /api/v1/quizzes/` and `GET /api/v1/quizzes/{id}/` → `QuizViewSet` (`apps/assessments/viewsets/quiz_viewset.py:9`) |
| **Permissions** | `AllowAny` (`apps/assessments/viewsets/quiz_viewset.py:18`) |

### Main Flow
1. `QuizViewSet` is a `ReadOnlyModelViewSet` with
   `queryset = Quiz.objects.filter(is_active=True)`.
2. List returns `QuizListSerializer` (compact summary); detail returns
   `QuizDetailSerializer` (full question set with answer choices).
3. `AnswerChoiceSerializer` excludes the `is_correct` field so correct
   answers are not exposed before submission.

### Note
No quiz authoring API exists. `QuizViewSet` is read-only.
`QuestionViewSet` and `AnswerChoiceViewSet` are not registered. Quizzes
are authored via Django admin or fixtures only (see Coverage Notes).

---

## UC-13: Student Submits Quiz Attempt (AxiomEngine Path)

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-13 |
| **Actor**       | Student |
| **Endpoint**    | `POST /api/v1/attempts/` → `AttemptViewSet.create` (`apps/assessments/viewsets/attempt_viewset.py:139`) |
| **Permissions** | `[IsAuthenticated, IsStudent]` (`apps/assessments/viewsets/attempt_viewset.py:115`) |

### Preconditions
- Student holds a valid access token.
- Target `Quiz` exists with `is_active=True`.

### Main Flow
1. Frontend POSTs body validated by `AttemptSubmitSerializer`
   (`apps/assessments/serializers/attempt_serializer.py:11-18`):
   ```json
   {
     "quiz_id":    1,
     "student_id": 2,
     "answers": [{"question_id": 1, "selected_choice_id": 3}]
   }
   ```
2. `create` resolves `LMSUser` and `Quiz`; returns 400 with
   `{"error": "validation_error", "details": "..."}` on missing records
   (`apps/assessments/viewsets/attempt_viewset.py:152-164`).
3. Creates `QuizAttempt` and bulk-inserts `AttemptAnswer` rows
   (lines 166-177).
4. Calls `ScoringService.score_and_evaluate(attempt)`
   (`apps/assessments/services/scoring_service.py:23`), which:
   - stamps `end_time`, aggregates correct answers per `question.concept_id`,
     sets `final_score` and `is_submitted=True` (lines 33-54);
   - creates `Evaluation` with `score`/`max_score` (lines 56-61);
   - creates one `FailedTopic` per concept not fully correct (lines 63-72);
   - creates `EvaluationTelemetry` with `time_on_task_seconds` computed
     from `end_time - start_time` and `clicks=0` (lines 74-84);
   - if failed concepts exist, calls
     `AxiomEngineClient().request_adaptive_plan(evaluation.pk)`
     (lines 88-91); on `AxiomEngineError` stores fallback
     `{"plan": [], "fallback": True}` (lines 92-96);
   - persists `adaptive_plan` on `QuizAttempt` (lines 98-100).
5. Response 201 merges `AttemptResultSerializer` with the service
   result dict (`apps/assessments/viewsets/attempt_viewset.py:183-186`).

### Response shape (201)
```json
{
  "id": 42, "student": 2, "quiz": 1,
  "start_time": "...", "end_time": "...",
  "final_score": "75.00", "is_submitted": true,
  "adaptive_plan": { /* see § Adaptive-plan envelope in 04_architecture.md */ },
  "score": 3.0, "max_score": 4.0,
  "failed_concepts": ["Polymorphism"],
  "evaluation_id": 17
}
```

### Adaptive-plan envelope — two possible shapes
On success (`apps/learning/services/axiom_service.py:120`):
```json
{
  "student_id": "2", "course_id": "CS101",
  "items": [{"topic": "...", "priority": 1, "prerequisite_chain": [],
             "explanation": "...", "resources": []}],
  "_meta": {"request_id": "...", "duration_ms": 120, "topics_requested": 1,
            "topics_planned": 1, "hallucinations_dropped": 0}
}
```
On fallback (`apps/learning/services/axiom_service.py:96-107`):
```json
{"plan": [], "fallback": true}
```

### Exceptions
- **Timeout / ConnectionError** → fallback envelope stored; 201 returned.
- **AxiomEngineError** → fallback envelope stored; 201 returned.
- **Missing student/quiz** → 400.

---

## UC-14: Student Reviews Own Quiz Attempts

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-14 |
| **Actor**       | Student |
| **Endpoints**   | `GET /api/v1/attempts/` and `GET /api/v1/attempts/{id}/` → `AttemptViewSet.list` / `.retrieve` (`apps/assessments/viewsets/attempt_viewset.py:197,232`) |
| **Permissions** | `[IsAuthenticated, IsStudent]` |

### Main Flow
1. `list` returns all `QuizAttempt` rows for `student=request.user`,
   ordered by `−start_time`, paginated (lines 206-215).
2. `retrieve` fetches a single attempt by `pk` with
   `student=request.user`; returns 404 if not owned (lines 243-246).
3. Both use `AttemptResultSerializer`.

---

## UC-15: Student Streams Proctoring Events

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-15 |
| **Actor**       | Student |
| **Endpoint**    | `POST /api/v1/proctoring/logs/` → `ProctoringViewSet.create` (`apps/assessments/viewsets/proctoring_viewset.py:100-121`) |
| **Permissions** | `[IsAuthenticated, IsStudent]` |

### Main Flow
1. Client sends body validated by `ProctoringBulkSerializer`
   (`apps/assessments/serializers/proctoring_serializer.py:13-18`):
   ```json
   {
     "events": [
       {
         "attempt":       42,
         "event_type":    "tab_switched",
         "timestamp":     "2026-04-17T10:00:00Z",
         "severity_score": 0.8
       }
     ]
   }
   ```
2. `event_type` must be one of `tab_switched`, `face_not_detected`,
   `multiple_faces` (`apps/assessments/models/proctoring_model.py:10-13`).
3. Bulk-creates one `ProctoringLog` per event.
4. Returns 201 with `{"ingested": <count>}`.

---

## UC-16: Tutor Reviews Course Analytics Dashboard

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-16 |
| **Actor**       | Tutor |
| **Endpoint**    | `GET /api/v1/analytics/course/{course_id}/dashboard/` → `TeacherDashboardViewSet.course_dashboard` (`apps/assessments/viewsets/analytics_viewset.py:131-136`) |
| **Permissions** | `[IsAuthenticated, IsTutor]` (`apps/assessments/viewsets/analytics_viewset.py:96`) |

### Main Flow
1. Path registered via
   `@action(detail=False, url_path=r"course/(?P<course_id>[^/.]+)/dashboard")`
   on the `analytics` router prefix.
2. Returns 404 if `course_id` does not match any `Course`.
3. Aggregates (lines 154-213):
   - `total_enrolled_students` — union of student PKs across
     `Evaluation` and `QuizAttempt` for the course;
   - `average_quiz_score` — `Avg(final_score)` over submitted, scored
     `QuizAttempt` rows;
   - `proctoring_alerts` — counts per `event_type`, **restricted to
     `CRITICAL_EVENT_TYPES = [TAB_SWITCHED, MULTIPLE_FACES]`**
     (lines 98-101). `FACE_NOT_DETECTED` is deliberately excluded;
   - `vark_distribution` — `Count` grouped by `vark_dominant` over
     enrolled students;
   - `top_failed_concepts` — top 3 `concept_id` by `fail_count` across
     `FailedTopic` rows.

### Response shape (200)
```json
{
  "course_id": 1,
  "course_code": "CS-201",
  "course_name": "Advanced Programming",
  "total_enrolled_students": 10,
  "average_quiz_score": 72.50,
  "proctoring_alerts": {"tab_switched": 6, "multiple_faces": 4},
  "vark_distribution": {"visual": 3, "aural": 2, "read_write": 3, "kinesthetic": 2},
  "top_failed_concepts": [{"concept_id": "Polymorphism", "fail_count": 3}]
}
```

---

## UC-17: Student Generates Certificate

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-17 |
| **Actor**       | Student |
| **Endpoint**    | `POST /api/v1/certificates/generate/` → `CertificateViewSet.generate` (`apps/learning/viewsets/certificate_viewset.py:77-129`) |
| **Permissions** | `[IsAuthenticated, IsStudent]` (`apps/learning/viewsets/certificate_viewset.py:22`) |

### Main Flow
1. Student POSTs `{"student_id": int, "course_id": int}`.
2. `CertificateGenerator.issue_certificate(student, course)` runs
   `_verify_eligibility` (`apps/learning/services/certification_service.py:52-63`),
   which requires at least one of:
   - `Evaluation` with `score >= PASSING_SCORE` (60.00,
     `certification_service.py:25`), or
   - `QuizAttempt` with `is_submitted=True` and
     `final_score >= PASSING_SCORE`.
3. If `(student, course)` already has a `Certificate`, returns it
   unchanged (idempotent, lines 96-104).
4. Otherwise, computes `certificate_hash = sha256(
   f"{student_id}:{course_id}:{issued_at_iso}")`
   (lines 28-40) and creates the row. `IntegrityError` from a concurrent
   issue is caught.

### Response shape (201)
```json
{
  "certificate_hash": "<64-char hex>",
  "issued_at":        "<iso8601>",
  "course_id":        1,
  "student_id":       5
}
```
(`apps/learning/viewsets/certificate_viewset.py:93-104`)

### Exceptions
- **403** — `CertificateEligibilityError`: student has not passed
  (`apps/learning/viewsets/certificate_viewset.py:112-119`).
  Body: `{"error": "not_eligible", "details": "..."}`.
- **400** — student or course not found.

---

## UC-18: Create Evaluation and Trigger AxiomEngine

This is a second, independent Axiom trigger path — distinct from UC-13
(quiz submission). It is invoked directly through the evaluation CRUD
endpoint.

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-18 |
| **Actor**       | Any authenticated user |
| **Endpoint**    | `POST /api/v1/evaluations/` → `EvaluationViewSet.create` (`apps/learning/viewsets/evaluation_viewset.py:42`) |
| **Permissions** | `[IsAuthenticated]` (`apps/learning/viewsets/evaluation_viewset.py:26`) |

### Main Flow
1. `EvaluationSerializer` (`apps/learning/serializers/evaluation_serializer.py:8`)
   validates `student`, `course`, `score`, `max_score`, optional
   `failed_topics[]`, optional nested `telemetry`; `create()` bulk-creates
   `FailedTopic` and optionally `EvaluationTelemetry` (lines 31-45).
2. If the saved evaluation has any `failed_topics`, the viewset calls
   `AxiomEngineClient().request_adaptive_plan(evaluation.pk)`
   (`apps/learning/viewsets/evaluation_viewset.py:60-63`).
3. Response 201 merges the serialized `Evaluation` with:
   - `adaptive_plan`: the `PlanResponse` dict on success, `null` on error;
   - `axiom_error`: present only on non-2xx or timeout
     (`apps/learning/viewsets/evaluation_viewset.py:64-80`).

### Difference from UC-13
Unlike the `ScoringService` path in UC-13, this path does **not**
substitute a `{"plan": [], "fallback": true}` envelope on error.
On failure `adaptive_plan` stays `null` and `axiom_error` carries the
details.

### Exceptions
- **AxiomEngineTimeout** — 201 returned with
  `axiom_error: {"error": "axiom_timeout", "details": "..."}`.
- **AxiomEngineError** — 201 returned with
  `axiom_error: {"error": "axiom_error", "status_code": N, "details": "..."}`.

---

## UC-19: Evaluation List / Retrieve / Update / Delete

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-19 |
| **Actor**       | Any authenticated user |
| **Endpoints**   | `GET/PUT/PATCH/DELETE /api/v1/evaluations/` and `…/{id}/` → `EvaluationViewSet` (ModelViewSet) |
| **Permissions** | `[IsAuthenticated]` for all non-create actions |

### Main Flow
Standard DRF `ModelViewSet` CRUD. No row-level scoping beyond
authentication is applied in `EvaluationViewSet.get_queryset` (returns
`Evaluation.objects.all()`). `EvaluationSerializer` is used for all
actions.

---

## UC-20: Evaluation Telemetry CRUD

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-20 |
| **Actor**       | Student (create); Student or Tutor (list/retrieve); Tutor (update/delete) |
| **Endpoint**    | `/api/v1/evaluation-telemetry/` → `EvaluationTelemetryViewSet` (`apps/assessments/viewsets/evaluation_telemetry_viewset.py:16`) |
| **Permissions** | Dynamic per action — see `get_permissions()` (lines 45-55) |

### Permission matrix

| Action               | Required role |
|----------------------|---------------|
| `create`             | `IsStudent`   |
| `list`, `retrieve`   | `IsAuthenticated` |
| `update`, `partial_update`, `destroy` | `IsTutor` |

### Row-level scoping
`get_queryset()` (lines 29-43): students see only telemetry where
`evaluation__student == request.user`; tutors see all rows.

### Request body (create)
```json
{
  "evaluation":          17,
  "time_on_task_seconds": 300,
  "clicks":               42
}
```

### Note
`ScoringService` (UC-13) auto-creates an `EvaluationTelemetry` row with
`clicks=0` and `time_on_task_seconds` computed from attempt duration
(`apps/assessments/services/scoring_service.py:74-84`). This UC covers
manual creation and management of additional telemetry records.

---

## UC-21: Tutor Queries Cognitive-Shadow Graph (Go Direct)

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-21 |
| **Actor**       | Tutor (or any frontend caller) |
| **Endpoint**    | `GET /api/v1/tutor/student/:student_id/cognitive-graph?topics=T1,T2` on the **Go service** (`axiom-reasoning-svc/internal/api/handlers.go:150-186`) |
| **Permissions** | None enforced at the Go layer (relies on network-level trust) |

### Note on routing
This endpoint does **not** pass through Django. The Angular client is
expected to call the Go service at `AXIOM_ENGINE_URL` directly. There is
no Django ViewSet or proxy that wraps this call.

### Main Flow
1. Client GETs the URL with optional `topics` query param (comma-
   separated concept IDs).
2. Handler calls `graph.GenerateCognitiveShadow(studentID, topics)`
   (`axiom-reasoning-svc/internal/graph/memory.go:188-235`), which
   classifies each node as `failed` / `learning` / `mastered` using
   the in-memory knowledge graph (19 hardcoded triples).
3. Returns `CognitiveGraphResponse`.

### Response shape (200)
```json
{
  "student_id": "2",
  "nodes": [
    {"id": "OOP", "status": "failed"},
    {"id": "Inheritance", "status": "learning"},
    {"id": "Variables", "status": "mastered"}
  ],
  "edges": [{"from": "Variables", "to": "OOP"}]
}
```

---

## UC-22: Health Check (Liveness Probe)

| Field           | Value |
|-----------------|-------|
| **ID**          | UC-22 |
| **Actor**       | Load balancer, orchestrator, or monitoring system |
| **Endpoint**    | `GET /health/` → `health_check` (`apps/learning/viewsets/health_viewset.py:16`) |
| **Permissions** | `AllowAny` |

### Main Flow
Returns 200 with `{"status": "ok"}` with no authentication and no
database query. Suitable for container healthcheck `CMD` and external
uptime monitors.

---

## Coverage Notes

The following features are **absent** from the API and therefore have
no use case:

- **Quiz authoring** — `QuizViewSet` is `ReadOnlyModelViewSet`; there is
  no `QuestionViewSet` or `AnswerChoiceViewSet` registered. Quizzes are
  managed via Django admin (`/admin/`) or database fixtures only.

- **Certificate verification** — `CertificateViewSet` exposes only the
  `generate` action (UC-17). There is no `GET /api/v1/certificates/verify/`
  or lookup-by-hash endpoint.

- **User registration / password reset** — no `UserViewSet.create` or
  password-management action is registered. User accounts are provisioned
  via Django admin.

- **Curriculum app soft-delete restore** — `SoftDeleteMixin` sets
  `is_deleted=True` but no ViewSet action reinstates a soft-deleted object.
  Recovery is only possible via Django admin or direct DB access.
