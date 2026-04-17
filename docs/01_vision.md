# 01 -- System Vision

> Every claim in this document is sourced from the codebase. File paths are
> relative to the repository root unless noted.

## 1. System Purpose

AxiomLMS is a Learning Management System built on Django 5.1.7
(`requirements.txt:1`) and Django REST Framework 3.15.2
(`requirements.txt:2`). It integrates with **AxiomEngine**, a standalone Go
microservice in the sister repository `axiom-reasoning-svc`, to generate
adaptive study plans from quiz-failure data. The Django monolith owns the
full academic lifecycle -- user accounts, the Career/Semester/Course/Module/
Lesson ontology, quizzes and attempts, proctoring logs, file-based
assignments/submissions, evaluations, and certificates. Intelligent plan
generation is delegated to the Go service synchronously over HTTP
(`apps/learning/services/axiom_service.py:80`).

Persistence: PostgreSQL (via `django.db.backends.postgresql`,
`core_lms/settings.py:86`) with connection config read from `DATABASE_URL`
or `POSTGRES_*` env vars (`core_lms/settings.py:74-93`); NeonDB is the
production target per `.env.example`.

File storage: AWS S3 via `django-storages` and `boto3`
(`core_lms/settings.py:162-193`).

Authentication: SimpleJWT with rotating refresh tokens
(`core_lms/settings.py:133-139`).

## 2. Actors

The code declares two user roles via `LMSUser.Role`
(`apps/learning/models/user_model.py:13-15`):

- `STUDENT = "STUDENT"`
- `TUTOR = "TUTOR"`

No other roles exist in the model.

### 2.1 Student

A `LMSUser` whose `role` is `STUDENT`
(`apps/learning/models/user_model.py:14`). Students hold a VARK learning
profile (`LMSUser.vark_dominant`,
`apps/learning/models/user_model.py:28-32`) chosen from
`{visual, aural, read_write, kinesthetic}`
(`apps/learning/models/user_model.py:17-21`). The `IsStudent` permission
class (`apps/learning/permissions.py:4`) gates student-only endpoints
(attempt submission, proctoring event ingest, certificate generation,
submission creation).

### 2.2 Tutor

A `LMSUser` whose `role` is `TUTOR` (`apps/learning/models/user_model.py:15`).
The `IsTutor` permission class (`apps/learning/permissions.py:21`) gates
write access to the academic ontology (Career, Semester, Course, Module,
Lesson, Resource, Assignment), the submission-grading action, and the
analytics dashboard.

### 2.3 System (Django backend + AxiomEngine)

The Django backend scores quizzes via `ScoringService`
(`apps/assessments/services/scoring_service.py:14`), creates `Evaluation`,
`FailedTopic`, and `EvaluationTelemetry` records, and synchronously calls
`AxiomEngineClient.request_adaptive_plan`
(`apps/learning/services/axiom_service.py:33`). The Go service receives a
POST to `/api/v1/adaptive-plan`
(`axiom-reasoning-svc/internal/api/handlers.go:47`), runs the GraphRAG
pipeline, and returns a structured `PlanResponse`
(`axiom-reasoning-svc/internal/domain/models.go:73-86`). Certificate
issuance is handled by `CertificateGenerator`
(`apps/learning/services/certification_service.py:16`).

## 3. Scope

### 3.1 Included

Three Django apps are registered in `INSTALLED_APPS`
(`core_lms/settings.py:26-28`):

- **learning** — users, academic ontology (Career→Semester→Course→Module→
  Lesson), resources, evaluations, failed topics, evaluation telemetry,
  certificates.
- **assessments** — quizzes, questions, answer choices, quiz attempts,
  attempt answers, proctoring logs, scoring service, analytics dashboard,
  evaluation-telemetry CRUD.
- **curriculum** — assignments and submissions, with S3-backed file
  uploads and a tutor-only grading action.

### 3.2 Not Included

Not derivable from the code: real-time chat, video conferencing, payment
processing. These are absent from the models, serializers, viewsets, and
URL routers; no dependencies such as Channels, Stripe, or LiveKit appear
in `requirements.txt`.

## 4. Quality Attributes

### 4.1 Security

- **JWT access token lifetime: 30 minutes**
  (`core_lms/settings.py:134`, `SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(minutes=30)`).
- **JWT refresh token lifetime: 7 days** (`core_lms/settings.py:135`).
- **Refresh rotation with blacklist** — `ROTATE_REFRESH_TOKENS=True`
  and `BLACKLIST_AFTER_ROTATION=True` (`core_lms/settings.py:136-137`);
  `rest_framework_simplejwt.token_blacklist` is installed
  (`core_lms/settings.py:25`).
- **RBAC** via custom DRF permission classes reading `LMSUser.role`
  (`apps/learning/permissions.py:13-18, 30-35`).
- **Token endpoint rate limit:** `RateLimitedTokenView` applies
  `@ratelimit(key="ip", rate="10/m", method="POST", block=False)` and
  returns HTTP 429 when exceeded
  (`apps/learning/viewsets/auth_viewset.py:35-55`).
- **Private-ACL S3** with pre-signed URLs: `STORAGES["default"]` configures
  `"default_acl": "private"`, `"querystring_auth": True`,
  `"querystring_expire": 3600` (`core_lms/settings.py:171-182`).
- **Security headers** — `X_FRAME_OPTIONS = "DENY"`,
  `SECURE_CONTENT_TYPE_NOSNIFF = True` (`core_lms/settings.py:214-215`);
  `SECURE_SSL_REDIRECT` driven by env (`core_lms/settings.py:211`).

### 4.2 Availability

`AxiomEngineClient.request_adaptive_plan` catches
`requests.exceptions.Timeout` and `requests.exceptions.ConnectionError`
and returns a fallback dict `{"plan": [], "fallback": True}` instead of
raising (`apps/learning/services/axiom_service.py:96-107`). Non-2xx
responses raise `AxiomEngineError`; in the scoring path,
`ScoringService` catches this and persists the same fallback to
`QuizAttempt.adaptive_plan`
(`apps/assessments/services/scoring_service.py:92-96`). The
`EvaluationViewSet.create` path does not catch `AxiomEngineError`; it
returns the evaluation with `axiom_error` metadata in the response
(`apps/learning/viewsets/evaluation_viewset.py:57-80`).

### 4.3 Maintainability

Each Django app follows a split-directory layout: `models/`,
`serializers/`, `viewsets/`, `services/`, one file per concern. A
`SoftDeleteMixin` / `SoftDeleteManager` / `AllObjectsManager` triple
(`core_lms/mixins.py`) is applied to eight models: `Career`, `Semester`,
`Course`, `Module`, `Lesson`, `Resource`, `Assignment`, `Submission`.
Soft-deleted rows are filtered out of the default manager and retained
for audit through `all_objects`. See `05_database_schema.md` for the
table-by-table soft-delete column list.

### 4.4 Observability

- Structured logging configured in `core_lms/settings.py:220-251`; root
  level defaults to `INFO` and is overridable via `LOG_LEVEL`.
- Public health check: `GET /health/` returns `{"status": "ok"}`
  (`apps/learning/viewsets/health_viewset.py:14-18`,
  `core_lms/urls.py:31`).
- Interactive API docs: `/swagger/` and `/redoc/` (`core_lms/urls.py:51-60`).
