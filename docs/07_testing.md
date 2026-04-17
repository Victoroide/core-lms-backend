# 07 - Testing Strategy and Commands

## Test Strategy Overview

AxiomLMS employs a four-layer testing strategy to ensure correctness across the
Django backend, the Go reasoning microservice, and their integration points.

### Layer 1: Unit Tests (Django TestCase)

Validate isolated model behavior, service logic, and storage callables without
HTTP overhead. Each test class targets a single concern and runs against a
throwaway PostgreSQL database spun up by Docker Compose.

### Layer 2: Integration Tests (DRF APITestCase)

Exercise full HTTP request/response flows through the DRF router, including JWT
authentication, permission checks, serializer validation, and paginated
responses. These tests hit the same endpoints that real clients consume.

### Layer 3: End-to-End Tests (Bash Script)

A suite of 48 curl-based tests executed inside the Docker environment against a
live API instance. The script performs a complete workflow: authentication,
resource creation, data retrieval, edge-case validation, and cleanup.

### Layer 4: Go Unit Tests

Cover knowledge graph algorithms and pipeline functions inside the AxiomEngine
microservice. These tests run with the standard Go test toolchain.

---

## Test Files

| File | Test Class | Tests |
|------|-----------|-------|
| `apps/learning/tests/test_models.py` | TestSoftDelete | 4 |
| `apps/learning/tests/test_models.py` | TestStorageCallables | 2 |
| `apps/learning/tests/test_models.py` | TestCertificate | 1 |
| `apps/learning/tests/test_views.py` | TestHealthCheck | 1 |
| `apps/learning/tests/test_views.py` | TestTokenRefresh | 3 |
| `apps/learning/tests/test_views.py` | TestTokenRateLimit | 1 |
| `apps/learning/tests/test_views.py` | TestVARKOnboarding | 3 |
| `apps/learning/tests/test_certificate_flow.py` | TestCertificateFlow | 3 |
| `apps/learning/tests/test_course_detail.py` | TestCourseNestedDetail | 2 |
| `apps/assessments/tests/test_scoring.py` | TestScoringService | 5 |
| `apps/assessments/tests/test_proctoring.py` | TestProctoringLog | 1 |
| `apps/assessments/tests/test_quiz_flow.py` | TestQuizFlow | 4 |
| `apps/assessments/tests/test_quiz_views.py` | TestQuizListDetail | 3 |
| `apps/assessments/tests/test_attempt_views.py` | TestAttemptRetrieval | 3 |
| `apps/assessments/tests/test_evaluations.py` | TestEvaluationCRUD | 6 |
| `apps/assessments/tests/test_telemetry.py` | TestEvaluationTelemetry | 3 |
| `apps/curriculum/tests/test_rbac.py` | TestRBAC | 5 |
| `apps/curriculum/tests/test_submission_isolation.py` | TestSubmissionIsolation | 5 |

---

## How to Run Each Suite

### Django Unit and Integration Tests

```bash
docker compose exec -e DJANGO_ENV=test web python manage.py test apps/ --verbosity=2
```

### End-to-End Script

```bash
docker compose exec web bash scripts/e2e_qa.sh
```

### Go Unit Tests

```bash
docker compose exec axiom-engine go test ./... -v -count=1
```

---

## Key Testing Patterns

### Mocking AxiomEngine

The Go microservice is mocked at the client boundary so that Django tests do not
require a running AxiomEngine instance:

```python
@patch("apps.assessments.services.scoring_service.AxiomEngineClient")
```

### Bypassing S3 Storage

File-upload tests replace the S3 backend with an in-memory store to avoid
network calls and AWS credentials:

```python
@override_settings(DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage")
```

### Minting JWT Tokens

Integration tests authenticate by generating tokens directly from a user
instance rather than hitting the token endpoint:

```python
token = RefreshToken.for_user(user).access_token
```

### Paginated Response Assertions

DRF pagination wraps results in an envelope. Tests access the inner data through
the standard keys:

```python
response.data["count"]    # total number of objects
response.data["results"]  # list of serialized objects on the current page
```

---

## E2E Script Interpretation

### Output Format

Each test prints a single line:

```
[PASS] [01] Health check returns 200
[FAIL] [02] Unauthenticated request returns 401
```

### Summary Line

The final line of output aggregates results:

```
PASSED=46/48 FAILED=2/48
```

### Exit Code

| Code | Meaning |
|------|---------|
| 0 | All 48 tests passed |
| 1 | One or more tests failed |

---

## Test Coverage by Endpoint

| Endpoint | Django Test File(s) | E2E Test(s) |
|----------|-------------------|-------------|
| /health/ | test_views.py (TestHealthCheck) | e2e [36] |
| /api/v1/auth/token/ | test_views.py (TestTokenRateLimit) | e2e [01-03] |
| /api/v1/auth/token/refresh/ | test_views.py (TestTokenRefresh -- valid, invalid, blacklisted after rotation) | e2e [37-38] |
| /api/v1/careers/ | -- | e2e [04-05, 34] |
| /api/v1/semesters/ | -- | e2e [06] |
| /api/v1/courses/ | test_course_detail.py | e2e [07-08, 44] |
| /api/v1/modules/ | -- | e2e [09] |
| /api/v1/lessons/ | -- | e2e [10, 23-25] |
| /api/v1/resources/ | -- | e2e [11-12] |
| /api/v1/assignments/ | test_rbac.py | e2e [14, 16] |
| /api/v1/submissions/ | test_rbac.py, test_submission_isolation.py | e2e [17-22, 35] |
| /api/v1/quizzes/ | test_quiz_views.py | e2e [39-41] |
| /api/v1/attempts/ | test_quiz_flow.py, test_attempt_views.py | e2e [26-30, 45-46] |
| /api/v1/proctoring/logs/ | test_proctoring.py | e2e [31] |
| /api/v1/analytics/course/{id}/dashboard/ | -- | e2e [32] |
| /api/v1/certificates/generate/ | test_certificate_flow.py | e2e [33] |
| /api/v1/evaluations/ | test_evaluations.py | e2e [43] |
| /api/v1/evaluation-telemetry/ | test_telemetry.py, test_evaluations.py (telemetry linked) | e2e [47-48] |
| /api/v1/users/{id}/onboard/ | test_views.py (TestVARKOnboarding) | e2e [42] |
