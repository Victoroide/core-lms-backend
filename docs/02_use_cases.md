# 02 -- Use Cases

> This file is a high-level index of the system's thirteen use cases
> (CU-01 through CU-13). Each row identifies the use case, its actor(s),
> the owning app, and the primary endpoint(s).
>
> **For full end-to-end flow detail** — preconditions, request bodies,
> response shapes, error cases, and source citations — see the
> per-use-case files in [`use_cases/`](use_cases/) (one file per CU).

---

## Use Case Index

| ID | Title | Actor(s) | App | Primary endpoint | Description |
|---|---|---|---|---|---|
| CU-01 | Gestionar sesión (login + refresh JWT) | Estudiante / Tutor | Auth | `POST /api/v1/auth/token/`, `POST /api/v1/auth/token/refresh/` | Authenticate against `RateLimitedTokenView` and rotate refresh tokens via `TaggedTokenRefreshView` (`apps/learning/viewsets/auth_viewset.py`). |
| CU-02 | Completar onboarding VARK | Estudiante | learning | `POST /api/v1/users/{id}/onboard/` | Submit VARK questionnaire answers; `UserViewSet.onboard` computes the dominant modality and persists `LMSUser.vark_dominant`. |
| CU-03 | Gestionar jerarquía académica | Tutor / Estudiante | learning | `/api/v1/{careers,semesters,courses,modules,lessons}/` | Read-only access for any authenticated user; `IsTutor`-gated CRUD writes on each ontology viewset. |
| CU-04 | Gestionar recursos de lección | Tutor / Estudiante | learning | `/api/v1/resources/` | Tutors upload `Resource` files via `ResourceViewSet`; any authenticated user retrieves them as direct public S3 URLs. |
| CU-05 | Gestionar asignaciones | Tutor | curriculum | `/api/v1/assignments/` | `AssignmentViewSet` CRUD scoped to `IsTutor` for writes (`apps/curriculum/viewsets/assignment_viewset.py`). |
| CU-06 | Entregar asignación | Estudiante | curriculum | `POST /api/v1/submissions/` | `SubmissionViewSet.create` accepts a multipart upload; the `(assignment, student)` unique constraint blocks duplicate submissions. |
| CU-07 | Gestionar entregas y calificar | Tutor | curriculum | `GET /api/v1/submissions/`, `PATCH /api/v1/submissions/{id}/grade/` | Tutors list every submission and grade via the `grade` `@action` (`submission_viewset.py:139-174`). |
| CU-08 | Consultar quizzes disponibles | Público / Estudiante | assessments | `GET /api/v1/quizzes/`, `GET /api/v1/quizzes/{id}/` | `QuizViewSet` is read-only with `AllowAny` on list/retrieve; `AnswerChoiceSerializer` excludes `is_correct`. |
| CU-09 | Rendir quiz con supervisión de proctoring | Estudiante | assessments + Go | `POST /api/v1/attempts/`, `POST /api/v1/proctoring/logs/` | `AttemptViewSet.create` bulk-inserts answers and calls `ScoringService.score_and_evaluate`, which synchronously requests an adaptive plan from AxiomEngine; proctoring events stream in via `ProctoringViewSet.create`. |
| CU-10 | Revisar intentos propios de quiz | Estudiante | assessments | `GET /api/v1/attempts/`, `GET /api/v1/attempts/{id}/` | Row-level scoping returns only the caller's `QuizAttempt` rows (`attempt_viewset.py:197-250`). |
| CU-11 | Revisar dashboard analítico del curso | Tutor | assessments | `GET /api/v1/analytics/course/{course_id}/dashboard/` | `TeacherDashboardViewSet.course_dashboard` aggregates enrolled students, average score, VARK distribution, top failed concepts, and proctoring alerts (excluding `face_not_detected`). |
| CU-12 | Consultar grafo cognitivo del estudiante | Tutor | AxiomEngine (Go) | `GET /api/v1/tutor/student/:student_id/cognitive-graph?topics=...` | **Direct call to the Go service on port 8080**, bypassing Django. Handler at `axiom-reasoning-svc/internal/api/handlers.go:154-193`; classification at `internal/graph/memory.go:191-250`. Returns `nodes[]` and `edges[]` for Cytoscape.js / D3 with each node tagged `failed`, `learning`, or `mastered`. |
| CU-13 | Generar certificado de curso aprobado | Estudiante | learning | `POST /api/v1/certificates/generate/` | `CertificateGenerator.issue_certificate` runs `_verify_eligibility` (requires `score >= PASSING_SCORE = 60.00`), computes the SHA-256 `certificate_hash`, and persists the `Certificate` row idempotently. |

---

## Coverage notes

The following capabilities are **absent** from the API and intentionally
have no use case:

- **Quiz authoring** — `QuizViewSet` accepts tutor CRUD on the `Quiz` model
  itself (`apps/assessments/viewsets/quiz_viewset.py:31-73`), but
  `QuestionViewSet` and `AnswerChoiceViewSet` are not registered. Question
  content is managed through the Django admin or seed fixtures.
- **User registration / password reset** — no `UserViewSet.create` or
  password-management action is exposed; accounts are provisioned via the
  Django admin.
- **Soft-delete restore** — `SoftDeleteMixin.delete()` flips
  `is_deleted=True`, but no viewset action restores a soft-deleted row.
  Recovery requires admin or direct DB access.
