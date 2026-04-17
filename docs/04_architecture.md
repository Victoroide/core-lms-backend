# 04 -- Architecture

> PUDS -- AxiomLMS Platform Architecture Document
> Version 1.0 | 2026-04-16

---

## 1. Deployment Diagram

```
+---------------------+         +-------------------------------+         +----------------------------+
|                     |  REST   |                               |  SQL    |                            |
|   Angular SPA       +-------->+   Django / DRF Monolith       +-------->+   NeonDB PostgreSQL        |
|   (port 4200)       |  CORS   |   (port 8000)                 |  SSL    |   (serverless, production) |
|                     |         |                               |         |                            |
+---------------------+         +-------+---------------+-------+         +----------------------------+
                                        |               |
                                        |               |
                          HTTP POST     |               |  boto3 / django-storages
                          /api/v1/      |               |
                          adaptive-plan |               |
                                        v               v
                         +--------------+--+    +-------+----------------+
                         |                 |    |                        |
                         | AxiomEngine Go  |    |   AWS S3               |
                         | (port 8080)     |    |   Private ACL          |
                         | Fiber + BAML    |    |   Pre-signed URLs      |
                         |                 |    |                        |
                         +--------+--------+    +------------------------+
                                  |
                                  | BAML fan-out
                                  v
                         +--------+--------+
                         |                 |
                         | Amazon Nova     |
                         | Micro (LLM)    |
                         |                 |
                         +-----------------+
```

---

## 2. Component Descriptions

### 2.1 Django Monolith (port 8000)

The backend is a Django 5.1.7 application using Django REST Framework. It is organized as a monolith containing three Django apps:

- **learning** -- User management, evaluations, telemetry, certificates, and failed-topic tracking.
- **assessments** -- Quizzes, questions, answer choices, quiz attempts, attempt answers, proctoring logs, and scoring.
- **curriculum** -- Academic ontology: careers, semesters, courses, modules, lessons, resources, assignments, and submissions.

Each app follows a split-topology layout:

```
app_name/
    models/          # One file per model
    serializers/     # One file per serializer
    viewsets/        # One file per viewset
    services/        # Business logic layer
    urls.py          # Router registration
    apps.py          # AppConfig
    admin.py         # Admin site registration
    permissions.py   # Custom permission classes (where applicable)
```

Responsibilities:

- JWT authentication via SimpleJWT (access + refresh token pair).
- Full CRUD for the academic ontology and assessment entities.
- Automated scoring of quiz attempts, including failed-topic extraction.
- Synchronous invocation of AxiomEngine for adaptive study plan generation.
- Certificate generation with SHA-256 hashing for tamper detection.
- File upload and pre-signed URL generation for S3-backed resources and submissions.
- Soft-delete across eight models via `SoftDeleteManager` and `AllObjectsManager`.

### 2.2 AxiomEngine Go Microservice (port 8080)

A standalone Go microservice responsible for GraphRAG reasoning over a concept topology derived from quiz results. It produces personalized adaptive study plans for students who complete assessments.

**Technology stack:** Go, Fiber HTTP framework, BAML (structured LLM orchestration).

**6-stage pipeline:**

1. **Subgraph extraction** -- Identifies the relevant concept subgraph from the student's failed topics and their dependency relationships.
2. **Topological sort** -- Orders concepts by prerequisite depth so the study plan follows a pedagogically valid sequence.
3. **Parallel BAML fan-out** -- Issues concurrent structured prompts to Amazon Nova Micro for each concept cluster, generating study recommendations.
4. **Merge and deduplication** -- Combines parallel LLM responses into a single coherent plan, removing redundant recommendations.
5. **Hallucination validation** -- Cross-checks generated content against the known concept topology to discard fabricated concepts or resources.
6. **Response enrichment** -- Attaches metadata (estimated study time, difficulty ratings, resource links) to each plan item.

**Resilience mechanisms:**

- Circuit breaker: opens after 3 consecutive failures, 15-second timeout before half-open retry.
- Rate limiting: 50 requests per minute per IP address, enforced at the Fiber middleware level.

### 2.3 AWS S3

Object storage for two categories of files:

- **Resources** -- Lesson-attached materials (PDFs, images, videos) uploaded by tutors.
- **Submissions** -- Student assignment submissions.

Configuration:

- Private ACL on all objects (no public access).
- Pre-signed URLs with 1-hour expiry (`AWS_QUERYSTRING_EXPIRE=3600`) for secure, time-limited download access.
- Managed via `django-storages` with the `boto3` backend.

### 2.4 NeonDB PostgreSQL

Serverless PostgreSQL provided by Neon, used as the production database.

- SSL required in production (`sslmode=require` in the connection string).
- Docker ephemeral PostgreSQL instance used for local development and CI testing.
- Connection pooling handled by Neon's built-in proxy.

---

## 3. Communication Patterns

### 3.1 Django to AxiomEngine (Synchronous HTTP)

| Aspect         | Detail                                                    |
|----------------|-----------------------------------------------------------|
| Method         | POST                                                      |
| Endpoint       | `http://<axiom-engine-host>:8080/api/v1/adaptive-plan`    |
| Content-Type   | `application/json`                                        |
| Timeout        | 3 seconds connect, 10 seconds read                        |
| Caller         | `AxiomEngineClient` in `learning/services/axiom_service.py` |
| Trigger        | Invoked by `ScoringService` after quiz attempt scoring     |

The call is synchronous. The Django request thread blocks until AxiomEngine responds or the timeout elapses. This is acceptable because adaptive plan generation is tied to a single user action (quiz submission) and is not on a high-throughput path.

### 3.2 Django to AWS S3 (boto3 via django-storages)

| Aspect         | Detail                                                    |
|----------------|-----------------------------------------------------------|
| Library        | `django-storages[s3]` with `boto3`                        |
| Upload         | `FileField` with `upload_to` callables for dynamic paths  |
| Download       | Pre-signed URL generation via the storage backend          |
| Authentication | IAM credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) |

File uploads are handled by DRF's multipart parser. The storage backend streams the file directly to S3 during model save.

### 3.3 Angular to Django (REST over CORS)

| Aspect         | Detail                                                    |
|----------------|-----------------------------------------------------------|
| Protocol       | HTTPS in production, HTTP in development                  |
| CORS origins   | `http://localhost:4200` (dev), production domain           |
| Authentication | Bearer token in `Authorization` header (JWT access token)  |
| Pagination     | `PageNumberPagination` with `PAGE_SIZE=20`                 |
| Content-Type   | `application/json` for all non-file endpoints              |

CORS is configured via `django-cors-headers` middleware.

---

## 4. Error Handling Strategy

### 4.1 AxiomEngine Failure

The `AxiomEngineClient` class wraps all HTTP calls to the Go microservice and handles failure modes explicitly:

| Failure Mode             | Handling                                                              |
|--------------------------|-----------------------------------------------------------------------|
| `ConnectionError`        | Caught by `AxiomEngineClient`. Returns fallback response.             |
| `Timeout`                | Caught by `AxiomEngineClient`. Returns fallback response.             |
| Non-2xx status code      | Caught by `AxiomEngineClient`. Returns fallback response.             |
| `AxiomEngineError`       | Caught by `ScoringService`. Stores fallback plan in `adaptive_plan`.  |

Fallback response structure:

```json
{
  "plan": [],
  "fallback": true
}
```

When a fallback is stored, the frontend displays a generic message indicating that personalized recommendations are temporarily unavailable. The student still receives their score and failed-topic breakdown.

### 4.2 S3 Pre-signed URL Expiry

Pre-signed URLs are generated with a 1-hour TTL (`AWS_QUERYSTRING_EXPIRE=3600`). If a client attempts to access an expired URL, AWS returns a 403 Forbidden response. The client must request a fresh URL from the Django API.

### 4.3 Database Integrity

- **Soft delete** prevents accidental data loss. Eight models carry `is_deleted` (BooleanField, default False) and `deleted_at` (DateTimeField, nullable) fields. The default manager (`SoftDeleteManager`) filters out soft-deleted records in all standard queries. An `AllObjectsManager` is available for administrative and seeding operations that need access to deleted records.
- **Foreign key constraints** are enforced at the database level. Cascade behavior is defined per relationship in the Django model `on_delete` parameter.
- **Unique constraints** (e.g., certificate per student-course pair, submission per assignment-student pair) are enforced at both the model and database levels.

### 4.4 Authentication Failures

| Scenario                  | Response Code | Detail                                         |
|---------------------------|---------------|-------------------------------------------------|
| Missing token             | 401           | `Authentication credentials were not provided.` |
| Expired access token      | 401           | `Token is invalid or expired.`                  |
| Insufficient permissions  | 403           | `You do not have permission to perform this action.` |
| Invalid refresh token     | 401           | `Token is invalid or expired.`                  |

JWT access tokens have a short lifetime. The Angular frontend uses the refresh token endpoint to obtain new access tokens transparently.
