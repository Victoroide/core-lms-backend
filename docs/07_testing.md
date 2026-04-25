# 07 -- Testing Strategy and Commands

> Test layers, counts, and run commands are sourced from `scripts/e2e_qa.sh`,
> `apps/*/tests/` directories, and `docker-compose.yml`. All paths
> relative to the Django repository root.

## Test Strategy Overview

AxiomLMS ships with a four-layer strategy:

### Layer 1 — Django unit tests (`TestCase`)

Isolated model/service/callable behavior. Files:
- `apps/learning/tests/test_models.py`
- `apps/learning/tests/test_certificate_flow.py`
- `apps/learning/tests/test_course_detail.py`
- `apps/assessments/tests/test_scoring.py`
- `apps/assessments/tests/test_proctoring.py`
- `apps/assessments/tests/test_quiz_flow.py`

### Layer 2 — DRF integration tests (`APITestCase`)

Full HTTP round-trip through routers, permissions, serializers. Files:
- `apps/learning/tests/test_views.py`
- `apps/assessments/tests/test_quiz_views.py`
- `apps/assessments/tests/test_attempt_views.py`
- `apps/assessments/tests/test_evaluations.py`
- `apps/assessments/tests/test_telemetry.py`
- `apps/curriculum/tests/test_rbac.py`
- `apps/curriculum/tests/test_submission_isolation.py`

### Layer 3 — End-to-end bash script

`scripts/e2e_qa.sh` declares `TOTAL=48` tests (line 13) and runs
curl-based requests against a live Docker-Compose stack. Test markers
numbered `[01]` through `[48]` appear as `# [NN]` comments in the
script; some numbers group multiple `assert_status` calls under a
single scenario.

### Layer 4 — Go unit tests

Live in the sister repo `axiom-reasoning-svc` under
`internal/**/*_test.go`. Not built into this repo's CI.

---

## Database configuration

`core_lms/settings.py:76-93` selects the datasource from the environment:

- `DJANGO_ENV=test` → Django connects to the local Docker `db` service
  using `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST=db`,
  `POSTGRES_PORT=5432`, `POSTGRES_DB`.
  `docker-compose.yml:db` uses ephemeral `tmpfs:/var/lib/postgresql/data`,
  so every `docker compose up` starts with a fresh schema.
- Any other value (unset / `"production"`) → parses `DATABASE_URL` —
  typically NeonDB with query params
  `sslmode=require&channel_binding=require` (see `.env.example`).

---

## Test files and classes

| File | Test class |
|------|------------|
| `apps/learning/tests/test_models.py` | `TestSoftDelete`, `TestStorageCallables`, `TestCertificate` |
| `apps/learning/tests/test_views.py` | `TestHealthCheck`, `TestTokenRefresh`, `TestTokenRateLimit`, `TestVARKOnboarding` |
| `apps/learning/tests/test_certificate_flow.py` | `TestCertificateFlow` |
| `apps/learning/tests/test_course_detail.py` | `TestCourseNestedDetail` |
| `apps/assessments/tests/test_scoring.py` | `TestScoringService` |
| `apps/assessments/tests/test_proctoring.py` | `TestProctoringLog` |
| `apps/assessments/tests/test_quiz_flow.py` | `TestQuizFlow` |
| `apps/assessments/tests/test_quiz_views.py` | `TestQuizListDetail` |
| `apps/assessments/tests/test_attempt_views.py` | `TestAttemptRetrieval` |
| `apps/assessments/tests/test_evaluations.py` | `TestEvaluationCRUD` |
| `apps/assessments/tests/test_telemetry.py` | `TestEvaluationTelemetry` |
| `apps/curriculum/tests/test_rbac.py` | `TestRBAC` |
| `apps/curriculum/tests/test_submission_isolation.py` | `TestSubmissionIsolation` |

Run `docker compose exec -e DJANGO_ENV=test web python manage.py test
apps/ --verbosity=2` to discover and execute all of them; test counts
change over time — rely on the runner output, not a frozen tally.

---

## How to run each suite

### Django unit + integration tests

```bash
docker compose exec -e DJANGO_ENV=test web \
  python manage.py test apps/ --verbosity=2
```

### End-to-end script

```bash
docker compose exec web bash scripts/e2e_qa.sh
```

Requires `curl` and `jq`. Both are installed in the image
(`Dockerfile:9-11`).

### Go unit tests (in the Axiom repo's container)

```bash
docker compose exec axiom-engine go test ./... -v -count=1
```

---

## Key testing patterns

### Mocking AxiomEngine

Django tests patch the client so no live Go service is required:
```python
@patch("apps.assessments.services.scoring_service.AxiomEngineClient")
```

`AxiomEngineClient`'s exception path
(`apps/learning/services/axiom_service.py:96-107`) — `requests.Timeout`
or `requests.ConnectionError` → `{"plan": [], "fallback": True}` — is
the primary isolation point for resilience tests.
`apps/assessments/tests/test_scoring.py` (`TestScoringService`) and
`apps/learning/tests/test_views.py` exercise this fallback path by
patching the client to raise; the persisted `QuizAttempt.adaptive_plan`
is asserted to equal the fallback envelope.

### Bypassing S3

File-upload tests override the storage backend:
```python
@override_settings(DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage")
```
(Note: the setting `DEFAULT_FILE_STORAGE` is deprecated in Django 5.x
in favor of the `STORAGES` dict, but the test-only override still
works because Django resolves both.)

### Minting JWTs directly

```python
from rest_framework_simplejwt.tokens import RefreshToken
access = RefreshToken.for_user(user).access_token
```

### Paginated response assertions

```python
response.data["count"]    # total
response.data["results"]  # current page
```

---

## E2E script interpretation

### Output format

`scripts/e2e_qa.sh:19-30` defines:
```text
[PASS] [NN] <description> (HTTP <status>)
[FAIL] [NN] <description> -- expected <x>, got <y>
  Response: <body>
```

### Summary

At the end, the script prints `PASSED=<p>/48 FAILED=<f>/48` and exits
with code 0 on a clean run, 1 otherwise. The `TOTAL=48` counter is set
at the top (`scripts/e2e_qa.sh:13`).

### Pre-conditions

Before invocation the stack must be running:
```bash
docker compose up --build -d
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py seed_data   # if available
```

Demo credentials referenced in the script (`scripts/e2e_qa.sh:64-80`):
- `prof_martinez` / `demo_pass_2026` — tutor
- `alice` / `demo_pass_2026` — student

---

## Test coverage by endpoint

Mapping is derived from the `apps/*/tests/` directory layout and
`scripts/e2e_qa.sh` test markers.

| Endpoint | Django test file(s) | E2E test marker(s) |
|----------|---------------------|--------------------|
| `/health/` | `test_views.py` (`TestHealthCheck`) | `[36]` |
| `/api/v1/auth/token/` | `test_views.py` (`TestTokenRateLimit`) | `[01]`, `[02]` |
| `/api/v1/auth/token/refresh/` | `test_views.py` (`TestTokenRefresh`) | `[37]`, `[38]` |
| `/api/v1/careers/` | — | `[04]`–`[05]`, `[34]` |
| `/api/v1/semesters/` | — | `[06]` |
| `/api/v1/courses/` | `test_course_detail.py` | `[07]`–`[08]`, `[44]` |
| `/api/v1/modules/` | — | `[09]` |
| `/api/v1/lessons/` | — | `[10]`, `[23]`–`[25]` |
| `/api/v1/resources/` | — | `[11]`–`[12]` |
| `/api/v1/assignments/` | `test_rbac.py` | `[14]`, `[16]` |
| `/api/v1/submissions/` | `test_rbac.py`, `test_submission_isolation.py` | `[17]`–`[22]`, `[35]` |
| `/api/v1/quizzes/` | `test_quiz_views.py` | `[39]`–`[41]` |
| `/api/v1/attempts/` | `test_quiz_flow.py`, `test_attempt_views.py` | `[26]`–`[30]`, `[45]`–`[46]` |
| `/api/v1/proctoring/logs/` | `test_proctoring.py` | `[31]` |
| `/api/v1/analytics/course/{id}/dashboard/` | — | `[32]` |
| `/api/v1/certificates/generate/` | `test_certificate_flow.py` | `[33]` |
| `/api/v1/evaluations/` | `test_evaluations.py` | `[43]` |
| `/api/v1/evaluation-telemetry/` | `test_telemetry.py` | `[47]`, `[48]` |
| `/api/v1/users/{id}/onboard/` | `test_views.py` (`TestVARKOnboarding`) | `[42]` |
