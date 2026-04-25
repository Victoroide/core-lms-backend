# 04 -- Architecture

> Sources live in two repositories:
> - Django: `core-lms-backend` (this repo)
> - Go:     `axiom-reasoning-svc` (sister repo)
>
> Every claim cites a specific file:line. The contract boundary between
> Django and Go is documented in § 3.1, with three known contract
> violations surfaced in § 5.

---

## 1. Deployment Diagram

```
+---------------------+          +--------------------------------+          +----------------------------+
|    Angular SPA      |  HTTPS   |  Django + Gunicorn monolith    |   TLS    |  NeonDB PostgreSQL         |
|                     +--------->+  core_lms.wsgi:application     +--------->+  (production) /            |
|                     |  CORS    |  port 8000 (PORT env)          |  SSL     |  Docker Postgres 15        |
+---------+-----------+          |                                |          |  (test / local)            |
          |                      +----+--------+------------+-----+          +----------------------------+
          |                           |        |            |
          |   direct GET              |  POST  |     boto3  |
          |   cognitive-graph         |        |            |
          |                           v        v            v
          |                 +---------+--+  +--+---------+  +-------------------------+
          |                 |            |  |            |  |                         |
          +---------------->+  AxiomEngine  |            |  |  AWS S3 (bucket policy) |
                            |  Go / Fiber   |            |  |  public-read via policy |
                            |  port 8080    |            |  |  no per-object ACL     |
                            +------+--------+            |  +-------------------------+
                                   |                     |
                                   | BAML                |
                                   v                     v
                            +------+--------+   (staticfiles bucket location
                            | AWS Bedrock   |    "static/", public URLs,
                            | Nova Micro    |    file_overwrite=True)
                            +---------------+
```

Ports:
- Django listens on `0.0.0.0:${PORT:-8000}` (Dockerfile:20,
  `d:/Repositories/python/django/core-lms-backend/Dockerfile#L20`).
- AxiomEngine listens on `":" + os.Getenv("PORT")` with a default of
  `"8080"` (`cmd/server/main.go:49-52, 120`).

---

## 2. Component Descriptions

### 2.1 Django Monolith

- Python 3.11 (Dockerfile base `python:3.11-slim`, `Dockerfile:1`).
- Django 5.1.7, DRF 3.15.2 (`requirements.txt:1-2`).
- Three apps, registered in `INSTALLED_APPS`
  (`core_lms/settings.py:26-28`): `apps.learning`, `apps.assessments`,
  `apps.curriculum`.
- Each app follows split-topology directories: `models/`, `serializers/`,
  `viewsets/`, `services/`, plus `urls.py` and `apps.py`.
- Global routing is in `core_lms/urls.py`, including Swagger/ReDoc at
  `/swagger/` and `/redoc/` (`core_lms/urls.py:51-60`).
- Authentication: SimpleJWT configured at `core_lms/settings.py:133-139`
  (access=30 min, refresh=7 d, rotation with blacklist).
- Default REST Framework permission class: `IsAuthenticated`
  (`core_lms/settings.py:121-123`); pagination: `PageNumberPagination`,
  `PAGE_SIZE=20` (`core_lms/settings.py:116-117`).
- Custom global exception handler
  (`core_lms.exception_handler.custom_exception_handler`) replaces
  unhandled 500 HTML pages with a JSON `{"detail": ...}` envelope
  (`core_lms/settings.py:127`).
- Responsibilities by app:
  - **`apps.learning`** — `LMSUser` and JWT auth viewsets
    (`viewsets/auth_viewset.py`, `viewsets/user_onboarding_viewset.py`),
    the academic ontology models `Career`, `Semester`, `Course`, `Module`,
    `Lesson`, `Resource` and their viewsets/serializers, plus
    `Evaluation`, `FailedTopic`, `EvaluationTelemetry`, `Certificate`.
    Owns the synchronous Go integration via `AxiomEngineClient`
    (`apps/learning/services/axiom_service.py:14`), certificate issuance
    via `CertificateGenerator`
    (`apps/learning/services/certification_service.py:16`), and the S3
    upload-path helper `resource_upload_path`
    (`apps/learning/services/storage_service.py:4-14`).
  - **`apps.assessments`** — `Quiz`, `Question`, `AnswerChoice`,
    `QuizAttempt`, `AttemptAnswer`, `ProctoringLog`. Owns
    `ScoringService` (`apps/assessments/services/scoring_service.py:14`),
    which is the only caller of `AxiomEngineClient` from the quiz path,
    and the analytics dashboard `TeacherDashboardViewSet`
    (`apps/assessments/viewsets/analytics_viewset.py:86-233`).
  - **`apps.curriculum`** — only `Assignment` and `Submission`, with the
    upload-path helper `submission_upload_path`
    (`apps/curriculum/services/storage_service.py:4-14`). The academic
    ontology (Career/Semester/Course/Module/Lesson/Resource) does **not**
    live in this app.
- File storage uses S3 with `querystring_auth=False` — `Resource.file` and
  `Submission.file` are exposed as direct public URLs via the bucket policy
  (no per-object ACL, no pre-signed query string); see § 2.3.

### 2.2 AxiomEngine Go microservice

- Entrypoint `cmd/server/main.go`.
- Framework: Fiber v2 with helmet, sliding-window rate limiter, logger,
  and panic-recovery middleware (`cmd/server/main.go:72-105`).
- JSON (de)serialization: `github.com/goccy/go-json`
  (`cmd/server/main.go:34, 64-65`).
- Logging: structured JSON via `log/slog`
  (`cmd/server/main.go:45-47`).
- Rate limit: **50 req/min per IP**, sliding window
  (`cmd/server/main.go:75-86`). On exceeded: HTTP 429 with
  `{"error": "rate_limit_exceeded", "details": "Too many requests. Max
  50 per minute."}`.
- Graceful shutdown on `SIGINT`/`SIGTERM` with 10-second timeout
  (`cmd/server/main.go:115-133`).

#### Reasoning pipeline (six stages)

All stages live in `internal/service/reasoning.go` and are orchestrated
by `ReasoningService.GeneratePlan` (line 94). The file's package comment
at `internal/service/reasoning.go:5-12` names them authoritatively:

| # | Stage | Source |
|---|-------|--------|
| 1 | Subgraph extraction — BFS over the in-memory graph at depth `subgraphDepth=2` | `reasoning.go:102-110`, `graph/memory.go:128-173` (`GetLocalSubgraph`) |
| 2 | Topological prerequisite sort — DFS post-order per failed topic | `reasoning.go:112-120`, `graph/memory.go:89-115` (`GetPrerequisiteChain`) |
| 3 | Parallel BAML fan-out — one `GenerateTopicPlan` call per failed topic via `errgroup`, each wrapped in a circuit breaker | `reasoning.go:122-175` |
| 4 | Merge & deduplicate per-topic plans | `reasoning.go:177-180` (`mergeAndDeduplicate`) |
| 5 | Hallucination guard — drop items whose `topic` is not a node in the graph | `reasoning.go` (later stages; referenced in package comment line 11) |
| 6 | Response enrichment with `_meta` pipeline telemetry only (no `estimated_study_time` or `difficulty` fields exist on `PlanItem`) — see `domain/models.go:91-111` | `reasoning.go` |

Per-topic LLM timeout: **15 seconds**
(`reasoning.go:83, 134-135`). Pipeline (request-level) timeout:
**20 seconds** (`internal/api/handlers.go:25, 101-102`).

#### Circuit breaker (sony/gobreaker)

Configured at `reasoning.go:62-78`:
- Name: `"bedrock-nova-micro"`
- MaxRequests (half-open probes): **2**
- Interval (closed-state counting window): **30 seconds**
- Timeout (open-state hold): **15 seconds**
- ReadyToTrip: opens after **3 consecutive failures**
- On open: `GeneratePlan` returns `ErrCircuitOpen`
  (`reasoning.go:36, 148-151`), which the handler maps to **HTTP 503**
  with `{"error": "service_unavailable", "details": "LLM backend
  circuit breaker is open; try again later"}`
  (`api/handlers.go:116-122`).

#### BAML / LLM

- Client: AWS Bedrock Nova Micro, model id
  `"amazon.nova-micro-v1:0"`, `max_tokens=2048`, `temperature=0.1`
  (`baml_src/clients.baml:1-14`).
- Retry policy `BedrockRetry`: `max_retries=2`, exponential backoff
  `delay_ms=500`, `multiplier=2.0`, `max_delay_ms=10000`
  (`baml_src/clients.baml:16-23`).
- BAML functions:
  - `GenerateTopicPlan(graph_context, target_topic, prerequisite_order,
    vark_profile, student_id, course_id) -> AdaptiveStudyPlan`
    (`baml_src/resume.baml:31-73`) — called once per failed topic in
    the fan-out.
  - `GenerateAdaptivePlan(graph_context, failed_topics, vark_profile)
    -> AdaptiveStudyPlan` (`baml_src/resume.baml:77-108`) — defined
    but **not** invoked by the current pipeline.
- Go bindings generated into `baml_client/` (`baml_src/generators.baml:6-20`).

#### Knowledge graph

- In-memory only (`internal/graph/memory.go:30-35`), seeded from 19
  hardcoded triples in `defaultTuples()`
  (`internal/graph/memory.go:241-264`) — nodes include `Polymorphism`,
  `Inheritance`, `Classes`, `Recursion`, `Graph Traversal`, `AVL Trees`,
  etc., related by `depends_on` or `is_a`.
- Data structure: two adjacency maps (`forward` and `reverse`), a
  `nodes` set, and an ordered `all` slice of `GraphTuple`
  (`graph/memory.go:30-35`).
- Traversal used by the pipeline:
  - `GetPrerequisiteChain(topic)` — DFS post-order following only
    `depends_on` and `is_a` edges (`graph/memory.go:89-115`).
  - `GetLocalSubgraph(topics, depth)` — depth-limited BFS over forward
    and reverse edges (`graph/memory.go:128-173`).
  - `GenerateCognitiveShadow(studentID, failedTopics)` — returns full
    `CognitiveGraphResponse` with every node classified as `failed`,
    `learning`, or `mastered` (`graph/memory.go:188-235`).

### 2.3 AWS S3 (default storage)

- Configured in `core_lms/settings.py:176-202`:
  - `"default"` backend: `S3Boto3Storage`, `default_acl=None`,
    `querystring_auth=False`,
    `file_overwrite=False`.
  - `"staticfiles"` backend: `S3Boto3Storage`,
    `location="static"`, `querystring_auth=False`,
    `file_overwrite=True`. Collected at container start via
    `python manage.py collectstatic --noinput` (`Dockerfile:20`).
- Bucket domain derived as
  `f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"`
  (`core_lms/settings.py:171`), with `STATIC_URL` set accordingly
  (line 173).
- Upload paths (server-computed):
  - `Resource.file` → `resources/{course_id}/{filename}`
    (`apps/learning/services/storage_service.py:4-14`).
  - `Submission.file` → `submissions/{student_id}/{filename}`
    (`apps/curriculum/services/storage_service.py:4-14`).
- Settings guard at `core_lms/settings.py:195-206` raises
  `ImproperlyConfigured` unless AWS credentials are provided (skipped
  for `test`, `makemigrations`, `collectstatic` invocations).

### 2.4 PostgreSQL

- Django picks the DSN at import time (`core_lms/settings.py:76-93`):
  - If `DJANGO_ENV != "test"` → parses `DATABASE_URL`.
  - Else → constructs `postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}
    @{POSTGRES_HOST:db}:{POSTGRES_PORT:5432}/{POSTGRES_DB}` for the
    Docker Postgres container (`docker-compose.yml:db`).
- `DATABASES["default"].OPTIONS` is populated from the DSN query string
  (line 92), so Neon-specific flags like `sslmode=require&
  channel_binding=require` (see `.env.example`) flow through as
  psycopg options.

---

## 3. Communication Patterns

### 3.1 Django → AxiomEngine (synchronous HTTP)

| Aspect | Value | Source |
|--------|-------|--------|
| Caller | `AxiomEngineClient` | `apps/learning/services/axiom_service.py:14` |
| Invoked from | `ScoringService.score_and_evaluate` (quiz-attempt path, CU-09) and `EvaluationViewSet.create` (evaluation-CRUD path) | `apps/assessments/services/scoring_service.py:88-96`; `apps/learning/viewsets/evaluation_viewset.py:60-63` |
| Method | `POST` | `axiom_service.py:90` |
| URL | `{AXIOM_ENGINE_URL}/api/v1/adaptive-plan` | `axiom_service.py:31, 80`; `core_lms/settings.py:157` |
| Content-Type | `application/json` | `axiom_service.py:94` |
| Connect / read timeouts | `(3, 10)` seconds | `axiom_service.py:11, 93` |

#### Request body (Django → Go)

Constructed at
[axiom_service.py:71-78](../apps/learning/services/axiom_service.py#L71-L78):

```json
{
  "student_id":  "<str(evaluation.student.pk)>",
  "course_id":   "<evaluation.course.code>",
  "failed_topics": ["<FailedTopic.concept_id>", ...],
  "vark_profile": "<LMSUser.vark_dominant>",
  "telemetry": {                      // only when EvaluationTelemetry exists
    "session_id":     "eval-<evaluation.pk>",
    "timestamp_unix": <int(evaluation.created_at.timestamp())>,
    "duration_ms":    <tel.time_on_task_seconds * 1000.0>,
    "client_version": "django-lms-1.0"
  }
}
```

Go receiver — `AdaptivePlanRequest`
([internal/domain/models.go:16-34](../../axiom-reasoning-svc/internal/domain/models.go#L16-L34)):

| JSON key | Go field | Go type |
|----------|----------|---------|
| `student_id` | `StudentID` | `string` |
| `course_id` | `CourseID` | `string` |
| `failed_topics` | `FailedTopics` | `[]string` (must be non-empty) |
| `vark_profile` | `VARKProfile` | `string` (non-empty) |
| `telemetry` | `Telemetry` | `*Telemetry`, omitempty |

Validation on the Go side (`internal/api/handlers.go:81-93`):
- 400 if `failed_topics` is empty.
- 400 if `vark_profile` is empty.

#### Response body (Go → Django, success)

Go `PlanResponse`
([internal/domain/models.go:73-86](../../axiom-reasoning-svc/internal/domain/models.go#L73-L86)):

```json
{
  "student_id": "...",
  "course_id":  "...",
  "items": [
    {
      "topic": "...",
      "priority": 1,
      "prerequisite_chain": ["...", "..."],
      "explanation": "...",
      "resources": [
        {"title": "...", "url": "...", "resource_type": "..."}
      ]
    }
  ],
  "_meta": {
    "subgraph_tuples": 12,
    "topics_processed": 2,
    "items_generated": 6,
    "items_after_validation": 5,
    "llm_latency_ms": 3240.5,
    "total_latency_ms": 3312.8
  }
}
```

Django does not reshape the response body. `AxiomEngineClient` returns
`response.json()` verbatim
(`apps/learning/services/axiom_service.py:120-126`), which the callers
persist directly into `QuizAttempt.adaptive_plan` (quiz-attempt path,
CU-09) or `response_data["adaptive_plan"]` (evaluation-CRUD path).

#### Adaptive-plan envelope (union of success and fallback)

The `adaptive_plan` field stored in DB and returned to clients is
heterogeneous:

| Variant | Keys | When |
|---------|------|------|
| **Success** | `student_id`, `course_id`, `items[]`, `_meta` | Go returns 2xx |
| **Fallback** | `plan: []`, `fallback: true` | Django caught `Timeout` or `ConnectionError` (`axiom_service.py:96-107`) — in the `ScoringService` code path only (scoring_service.py:92-96 also substitutes fallback on `AxiomEngineError`). The `EvaluationViewSet` path never writes a fallback envelope; on error, `adaptive_plan` is `null` and `axiom_error` is populated instead (`evaluation_viewset.py:64-78`). |

Clients must handle both shapes — see § 5 (CV-02).

#### Error responses from Go

| Status | JSON payload | Trigger |
|--------|--------------|---------|
| 400 | `{"error":"invalid_request_body"\|"validation_error","details":...}` | body parse failure, empty `failed_topics`, empty `vark_profile` (`handlers.go:72-92`) |
| 429 | `{"error":"rate_limit_exceeded","details":"Too many requests. Max 50 per minute."}` | sliding-window limiter (`main.go:75-86`) |
| 500 | `{"error":"reasoning_failed","details":...}` | generic pipeline failure (`handlers.go:123-127`) |
| 503 | `{"error":"service_unavailable","details":"LLM backend circuit breaker is open; try again later"}` | circuit open (`handlers.go:116-122`) |
| 504 | `{"error":"gateway_timeout","details":"LLM reasoning exceeded deadline"}` | request-level 20s context deadline (`handlers.go:109-114`) |

### 3.2 Angular → AxiomEngine directly (cognitive-shadow graph)

`GET /api/v1/tutor/student/:student_id/cognitive-graph?topics=...`
(`cmd/server/main.go:109-112`, handler at
`internal/api/handlers.go:150-186`). The path param is echoed as
`student_id`; the `topics` query string is comma-separated. Returns
`CognitiveGraphResponse` with `nodes[]` (each node classified as
`failed`, `learning`, or `mastered`) and `edges[]`
(`internal/domain/models.go:163-208`). **No Django code calls this
endpoint.**

### 3.3 Django → AWS S3 (boto3)

- Library: `django-storages[s3]` + `boto3` (`requirements.txt:9-10`).
- Upload: DRF multipart parser → `FileField` → `S3Boto3Storage.save()`.
- Download: the serializer renders `file.url`, which `S3Boto3Storage`
  resolves to a direct public URL via `AWS_S3_CUSTOM_DOMAIN` (no query-string auth).

### 3.4 Angular → Django (REST)

- JWT Bearer token in `Authorization` header; access tokens expire in
  30 minutes.
- CORS origins configurable via `CORS_ALLOWED_ORIGINS`
  (`core_lms/settings.py:45-51`), default `"http://localhost:4200"`.
- Pagination envelope `{count, next, previous, results}` returned for
  all list endpoints.

---

## 4. Error Handling

### 4.1 AxiomEngine failures (Django side)

| Failure | Django reaction | Source |
|---------|------------------|--------|
| `requests.exceptions.Timeout` | returns `{"plan": [], "fallback": true}` | `axiom_service.py:96-100` |
| `requests.exceptions.ConnectionError` | returns `{"plan": [], "fallback": true}` | `axiom_service.py:101-107` |
| Non-2xx response | raises `AxiomEngineError(status_code, detail)` | `axiom_service.py:109-118` |
| `AxiomEngineError` in `ScoringService` | caught, stores fallback envelope on `QuizAttempt.adaptive_plan` | `scoring_service.py:92-96` |
| `AxiomEngineTimeout` or `AxiomEngineError` in `EvaluationViewSet.create` | response includes `axiom_error: {...}`; `adaptive_plan` stays `null` | `evaluation_viewset.py:64-78` |

### 4.2 S3 file access

File URLs are direct public links (no query-string auth). Access is
controlled by the S3 bucket policy which grants `s3:GetObject` on
`static/*`, `submissions/*`, and `resources/*` prefixes. URLs do not
expire.

### 4.3 Database integrity

- Soft-delete on eight models (see `01_vision.md` § 4.3 and
  `05_database_schema.md` § 4).
- Unique constraints enforced at the schema level: `Certificate` on
  `(student, course)`; `Submission` on `(assignment, student)`;
  `AttemptAnswer` on `(attempt, question)`; `Semester` on `(career,
  number, year)`.
- `core_lms.exception_handler.custom_exception_handler` catches
  unhandled exceptions and returns JSON 500
  (`core_lms/exception_handler.py:12-35`).

### 4.4 Authentication failures

| Situation | Response |
|-----------|----------|
| Missing/invalid JWT | DRF 401 with `{"detail": "Authentication credentials were not provided."}` or `"Token is invalid or expired."` |
| Wrong role | `IsStudent`/`IsTutor` returns 403 with `message` attribute of the permission class |
| 10/min token rate exceeded | 429 from `RateLimitedTokenView` (`apps/learning/viewsets/auth_viewset.py:42-55`) |

---

## 5. Contract Violations (flag, do not silently fix)

These are code-level discrepancies between Django and Go as of commit
`555fc67` on `main`. They should be resolved in code, not masked in the
docs.

### CV-01 — VARK enum mismatch

- Django: `LMSUser.VARKProfile.AURAL = "aural"`
  (`apps/learning/models/user_model.py:19`) and the onboarding endpoint
  enforces the same spelling
  (`apps/learning/viewsets/user_onboarding_viewset.py:15`).
- Go: the `AdaptivePlanRequest` docstring and the BAML `resume.baml`
  prompt both use `"auditory"`
  (`axiom-reasoning-svc/internal/domain/models.go:28`,
  `axiom-reasoning-svc/baml_src/resume.baml`).
- When an aural-dominant student triggers plan generation, Django sends
  `"aural"`; the Go handler accepts any non-empty string but the BAML
  resource-type VARK mapping expects one of
  `{visual, auditory, read_write, kinesthetic}`. Generated resources
  may not strictly match the student's modality.

### CV-02 — Heterogeneous `adaptive_plan` envelope

See § 3.1 table. The success envelope uses `items` + `_meta`; the
fallback envelope uses `plan` + `fallback`. Consumers (frontend, tests,
downstream analytics) must branch on the presence of `fallback` to
disambiguate. No single schema covers both cases; resolution would
require the fallback path to either produce an empty `items[]` with
`_meta` zeroed-out, or a normalised `status` field on both.

### CV-03 — `_meta` underscore prefix

Go serialises pipeline telemetry under the key `_meta`
(`internal/domain/models.go:85`). All other top-level keys are
unprefixed. Clients that strip underscore-prefixed keys (e.g. some
JSON post-processors) will drop pipeline observability data silently.
Rename or document explicitly on the client side.
