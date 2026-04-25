# CU-09 — Rendir quiz con supervisión de proctoring

## Overview

A student starts a quiz from inside the course viewer or the dashboard's diagnostic orchestrator, answers every question through `QuizPlayerComponent`, and submits. Django's `AttemptViewSet.create` writes a `QuizAttempt` and bulk-creates `AttemptAnswer` rows; `ScoringService.score_and_evaluate` then computes the score, creates the corresponding `Evaluation`, `FailedTopic`, and `EvaluationTelemetry` rows, and synchronously requests an adaptive plan from AxiomEngine for any failed concept. AxiomEngine runs a six-stage GraphRAG pipeline and returns a structured `PlanResponse`; on failure Django stores `{"plan": [], "fallback": true}` and still returns HTTP 201. Proctoring telemetry is the design intent for this flow but is not currently implemented in the Angular codebase.

## Actors and Preconditions

- Actor: Student.
- The caller is authenticated with `activeRole = 'STUDENT'` and `request.user.role == 'STUDENT'` server-side.
- A quiz with at least one question and one correct choice exists; questions reference concept IDs that map to nodes in the AxiomEngine knowledge graph for the adaptive plan to find a non-empty subgraph.
- For the adaptive-plan path: `LMSUser.vark_dominant` is set (CU-02 has been completed) so AxiomEngine can bias resource selection by modality.
- Quiz detail has been loaded into `quizStore.selectedQuizDetail()` either through `CourseViewerPageComponent` or `DiagnosticOrchestratorComponent`.

## Frontend Entry Point

- Course-viewer entry: `/student/course/:courseId` → `CourseViewerPageComponent` ([src/app/pages/student/course-viewer-page/course-viewer-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/student/course-viewer-page/course-viewer-page.component.ts)) → sidebar quiz click → `selectQuiz(quizId)` → `<app-quiz-player [quiz]="..." />` rendered in the main pane.
- Orchestrator entry: `/student` → `StudentDashboardPageComponent` → `<app-adaptive-plan-form />` → `<app-diagnostic-orchestrator />` ([src/app/features/reasoning/diagnostic-orchestrator/diagnostic-orchestrator.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/reasoning/diagnostic-orchestrator/diagnostic-orchestrator.component.ts)) — `step()` signal walks `select → quiz → waiting → result`.
- Player component: `QuizPlayerComponent` ([src/app/features/reasoning/quiz-player/quiz-player.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/reasoning/quiz-player/quiz-player.component.ts)) — pure presentation, emits `submitted` and `cancelled`.
- Trigger: the "Submit" button at the bottom of `QuizPlayerComponent`. The `submit()` method emits `submitted.emit(answers)` only when every question has a selected choice (`allAnswered` getter).
- Proctoring trigger: **none.** There is no `face-api.js` import, no `document.visibilitychange` listener, and no proctoring batch upload in the current Angular codebase. [verify: searched `src/app` for `face-api`, `visibilitychange`, `proctoring`; only `proctoring_alerts` references in the analytics dashboard schema (CU-11) were found.] The `ProctoringViewSet` endpoint exists server-side and is documented below for completeness.

## End-to-End Flow

### Quiz submission path

1. Student opens the course viewer, picks a quiz, and `CourseViewerPageComponent.selectQuiz(quizId)` calls `quizStore.loadQuizDetail(quizId)` and toggles the player.
2. `QuizPlayerComponent` renders each `Question` as a card with PrimeNG radio buttons; `(change)` events call `onAnswerSelected(questionId, choiceId)` which writes to a local `signal<Record<number, number>>({})`.
3. `allAnswered` (computed getter) is true once `selectedAnswers` has an entry for every question.
4. Student clicks Submit. `submit()` emits `submitted.emit(answers)` where `answers: AttemptAnswerInput[] = [{ question_id, selected_choice_id }, ...]`.
5. The host (course viewer or orchestrator) handles the emission. Both paths converge on calling the API:
   - Course viewer: `CourseViewerPageComponent.onQuizSubmitted(answers)` invokes `attemptApi.submitAttempt({ quizId, studentId, answers })` directly, then navigates to `/student?attemptId=<id>`.
   - Orchestrator: `DiagnosticOrchestratorComponent.onQuizSubmitted(answers)` calls `reasoningStore.runDiagnosticFromAttempt({ quizId, studentId, answers })` which submits the attempt and orchestrates the post-submit polling for async mode.
6. `AttemptApiService.submitAttempt(input)` ([src/app/entities/assessment/api/attempt.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/assessment/api/attempt.api.ts)) calls `djangoApi.post<AttemptResultResponse>('/api/v1/attempts/', { quiz_id, student_id, answers })`.
7. `baseUrlInterceptor` prepends `environment.djangoApiUrl`; `authInterceptor` attaches `Authorization: Bearer ${accessToken}`.
8. Django routes `POST /api/v1/attempts/` from `apps/assessments/urls.py` to `AttemptViewSet.create` ([apps/assessments/viewsets/attempt_viewset.py](../../apps/assessments/viewsets/attempt_viewset.py) lines 139-186).
9. `AttemptViewSet.permission_classes = [IsAuthenticated, IsStudent]`. `AttemptSubmitSerializer` validates `quiz_id`, `student_id`, and `answers[].{question_id, selected_choice_id}`.
10. The view resolves `LMSUser` and `Quiz`; if either is missing it returns HTTP 400 `{"error": "validation_error", "details": "..."}`.
11. The view creates `QuizAttempt(student, quiz)` and `bulk_create([AttemptAnswer(...)])`.
12. The view calls `ScoringService.score_and_evaluate(attempt)` ([apps/assessments/services/scoring_service.py](../../apps/assessments/services/scoring_service.py)).

### Scoring pipeline

13. `ScoringService.score_and_evaluate` stamps `attempt.end_time = timezone.now()`, aggregates correct vs total per `question.concept_id`, computes raw `final_score` (sum of correct answers), `max_score = total questions`, and sets `is_submitted=True`.
14. The service creates `Evaluation(student, course, score, max_score)` for the underlying course, then one `FailedTopic(evaluation, concept_id, score, max_score)` per concept that did not reach perfect score.
15. The service creates `EvaluationTelemetry(evaluation, time_on_task_seconds=delta_seconds, clicks=0)` — `clicks` is hard-coded to 0 because no click telemetry is gathered upstream.
16. If `failed_concepts` is non-empty, `ScoringService` calls `AxiomEngineClient().request_adaptive_plan(evaluation.pk)` ([apps/learning/services/axiom_service.py](../../apps/learning/services/axiom_service.py)).

### AxiomEngine path

17. `AxiomEngineClient.request_adaptive_plan` builds the JSON `{ student_id, course_id, failed_topics, vark_profile, telemetry }` and posts to `${AXIOM_ENGINE_URL}/api/v1/adaptive-plan` with timeouts `(3, 10)` seconds.
18. The Go service routes the request through Fiber's sliding-window rate limiter (50 req/min/IP) to `Handler.handleAdaptivePlan` ([axiom-reasoning-svc/internal/api/handlers.go](../../../axiom-reasoning-svc/internal/api/handlers.go) lines 68-136). The handler enforces a 20-second per-request timeout and a 15-second per-LLM-call timeout.
19. AxiomEngine runs the six-stage pipeline implemented in `internal/service/reasoning.go:94`:
    1. **Subgraph extraction** — `graph.GetLocalSubgraph(failedTopics, depth=2)` performs BFS over forward and reverse edges in the in-memory graph (`internal/graph/memory.go:128-173`).
    2. **Topological sort** — `graph.GetPrerequisiteChain(topic)` performs DFS post-order following only `depends_on` and `is_a` edges to produce a prerequisite chain per failed topic (`memory.go:89-115`).
    3. **Parallel BAML fan-out** — one `GenerateTopicPlan` BAML call per failed topic via `errgroup`, each wrapped in the `bedrock-nova-micro` circuit breaker (`reasoning.go:62-78, 122-175`). The breaker opens after 3 consecutive failures (15-second open hold, 30-second window, 2 half-open probes).
    4. **Merge & deduplication** — `mergeAndDeduplicate` collapses duplicate topics across per-topic plans and re-numbers priorities (`reasoning.go:177-180`).
    5. **Hallucination guard** — items whose `topic` is not a node in the graph are dropped (`reasoning.go`, package comment line 11).
    6. **Response enrichment** — pipeline telemetry is attached to `_meta` (`subgraph_tuples`, `topics_processed`, `items_generated`, `items_after_validation`, `llm_latency_ms`, `total_latency_ms`). The Go domain model `PlanItem` does **not** carry `estimated_study_time` or `difficulty` fields.
20. The Go service returns `PlanResponse { student_id, course_id, items[], _meta }` with HTTP 200, or one of {400 invalid body, 429 rate-limited, 503 circuit open, 504 deadline exceeded} on failure.
21. Back in Django, `AxiomEngineClient` either returns `response.json()` verbatim or, on `requests.Timeout`/`ConnectionError`, returns `{"plan": [], "fallback": True}`. On non-2xx it raises `AxiomEngineError`; `ScoringService` catches the exception and substitutes the same fallback envelope.
22. `ScoringService` writes the plan into `attempt.adaptive_plan` (JSONField) via `attempt.save(update_fields=['adaptive_plan', ...])`.
23. `AttemptViewSet.create` merges `AttemptResultSerializer(attempt).data` with the scoring service's return dict (`score`, `max_score`, `failed_concepts`, `evaluation_id`) and returns HTTP 201.

### Angular post-submit handling

24. `ReasoningStore.runDiagnosticFromAttempt(input)` ([src/app/entities/reasoning/model/reasoning.store.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/reasoning/model/reasoning.store.ts)) reads the attempt response, calls `applyAttemptResult(attempt)`, and updates `diagnosticStatus` to one of `success | fallback | pending | error`.
   - If `attempt.adaptive_plan.items` is present → `success`. The store writes `adaptivePlan` and `lastAttemptId` into state.
   - If `adaptive_plan.fallback === true` → `fallback`; the orchestrator transitions to `step='result'` and shows the empty-state message.
   - If `adaptive_plan.job_id` is present (async mode) → `pending`; the orchestrator's effect at line 100-118 starts a 4-second polling loop calling `reasoningStore.refreshAttemptResult(attemptId, { silent: true })` until `pending` clears or `error` raises.
25. The orchestrator step transitions to `result`, automatically calls `reasoningStore.loadCognitiveGraph(studentId, failedTopics)` (CU-12) when `showCognitiveShadow=true`, and renders `<app-adaptive-plan-timeline />` with the plan items.

### Proctoring stream (server-side reachable; not driven by the Angular SPA)

26. The endpoint `POST /api/v1/proctoring/logs/` exists and works. It is routed to `ProctoringViewSet.create` ([apps/assessments/viewsets/proctoring_viewset.py](../../apps/assessments/viewsets/proctoring_viewset.py)).
27. `ProctoringBulkSerializer` validates `events: [{attempt, event_type, timestamp, severity_score}]` where `event_type ∈ {tab_switched, face_not_detected, multiple_faces}`.
28. The view bulk-creates `ProctoringLog` rows and returns HTTP 201 `{"ingested": <count>}`. The current Angular codebase does not invoke this endpoint; it is exercised through the E2E bash script (`scripts/e2e_qa.sh`).

## Angular Implementation

- `AttemptApiService.submitAttempt(input: AttemptSubmitInput): Observable<AttemptResultResponse>` — POST to `/api/v1/attempts/`. The store derives `AttemptSubmitRequest` from the camelCase input (`quiz_id`, `student_id`, `answers`).
- `AttemptApiService.getAttempt(attemptId: number): Observable<AttemptResultResponse>` — GET for polling.
- Types ([src/app/entities/assessment/model/attempt.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/assessment/model/attempt.types.ts)):
  - `AttemptSubmitInput = { quizId, studentId, answers: AttemptAnswerInput[] }` and `AttemptAnswerInput = { question_id, selected_choice_id }`.
  - `AttemptResultResponse = { id, student, quiz, start_time, end_time, final_score, is_submitted, adaptive_plan, score?, max_score?, failed_concepts?, evaluation_id?, axiom_error?, job_id? }`.
  - `AttemptAdaptivePlanEnvelope = AdaptivePlanResponse | AttemptAdaptiveFallback | AttemptAdaptivePending | null`.
- `QuizPlayerComponent`:
  - Inputs: `@Input() quiz!: QuizDetailResponse`, `@Input() isSubmitting = false`.
  - Outputs: `@Output() submitted = new EventEmitter<AttemptAnswerInput[]>()`, `@Output() cancelled = new EventEmitter<void>()`.
  - State: `selectedAnswers = signal<Record<number, number>>({})`. Computed getters: `answeredCount`, `totalQuestions`, `progressValue`, `allAnswered`.
  - No timer is implemented despite `Quiz.time_limit_minutes` being part of the payload [verify: no countdown component or `setInterval` in the player].
- `DiagnosticOrchestratorComponent`:
  - State machine signal: `step = signal<'select' | 'quiz' | 'waiting' | 'result'>('select')`.
  - Reads `_studentId` from the JWT in an effect (uses `extractJwtPayload(sessionStore.accessToken())` to read `user_id`).
  - Effect at lines 100-118 runs `interval(4000)` while `reasoningStore.diagnosticStatus()` is `'pending'` or `'fallback'`, calling `refreshSilent(attemptId)` until status leaves the polling set.
  - Effect at lines 130-146 advances `step` to `'result'` when status is `'success'` and triggers `reasoningStore.loadCognitiveGraph(studentId, failedTopics)` when `showCognitiveShadow=true`.
  - Effect on error toasts via `GlobalToastService.error('Diagnostic failed', error)`.
- `ReasoningStore` orchestrates both the sync and async paths:
  - `runDiagnosticFromAttempt(input)` → posts the attempt, sets `diagnosticStatus='loading'`, then calls `applyAttemptResult(response)`.
  - `applyAttemptResult(attempt)` uses type guards `isAdaptivePlanResponse`, `isAdaptivePlanFallback`, and `normalizeJobId` to classify the response and update `diagnosticStatus`, `jobId`, `fallbackReason`, `lastAttemptId`, and `adaptivePlan`.
  - `refreshAttemptResult(attemptId, { silent })` polls `attemptApi.getAttempt(attemptId)` and re-applies the result.
- Template: `<app-adaptive-plan-timeline [items]="store.adaptivePlan()?.items ?? []" [status]="store.diagnosticStatus()" [llmLatencyMs]="store.adaptivePlan()?._meta?.llm_latency_ms ?? null" [lastAttemptId]="store.lastAttemptId()" />`.

## Backend Implementation

- Quiz submission endpoint: `POST /api/v1/attempts/` → `AttemptViewSet.create` (DRF `ViewSet`, not `ModelViewSet`).
- Permissions: class-level `[IsAuthenticated, IsStudent]`.
- Serializers (`apps/assessments/serializers/attempt_serializer.py`): `AttemptSubmitSerializer` for input; `AttemptResultSerializer` for output. The view merges the result with `score / max_score / failed_concepts / evaluation_id` from the service.
- Service: `ScoringService.score_and_evaluate(attempt: QuizAttempt) -> dict` at `apps/assessments/services/scoring_service.py:23-108`.
- Sub-service: `AxiomEngineClient.request_adaptive_plan(evaluation_id: int)` at `apps/learning/services/axiom_service.py:33-126`. Timeout `(3, 10)` seconds (connect, read).
- Proctoring endpoint: `POST /api/v1/proctoring/logs/` → `ProctoringViewSet.create` (`apps/assessments/viewsets/proctoring_viewset.py`). Serializer: `ProctoringBulkSerializer`.
- Models written: `assessments.QuizAttempt`, `assessments.AttemptAnswer`, `learning.Evaluation`, `learning.FailedTopic`, `learning.EvaluationTelemetry`, `assessments.QuizAttempt` (update for `adaptive_plan`), `assessments.ProctoringLog` (when the proctoring endpoint is invoked).
- Status codes: 201 on success (even when AxiomEngine fails — the fallback envelope is persisted), 400 on validation/missing FK, 401 on missing JWT, 403 on wrong role, 429 on per-IP burst at the AxiomEngine boundary (Go side), 503 if the Go circuit breaker is open, 504 on Go deadline exceeded.

## Data Model Involvement

| Order | Model | Operation | Notes |
|---|---|---|---|
| 1 | `assessments.QuizAttempt` | Create | Initial row before answer insertion. |
| 2 | `assessments.AttemptAnswer` | Bulk create | One row per answer; `unique_together = (attempt, question)`. |
| 3 | `assessments.QuizAttempt` | Update | `end_time`, `final_score`, `is_submitted` set by `ScoringService`. |
| 4 | `learning.Evaluation` | Create | Captures raw correct count and total questions for the course. |
| 5 | `learning.FailedTopic` | Create (per concept) | One row per concept that didn't reach perfect score; `concept_id` matches a node in the AxiomEngine knowledge graph. |
| 6 | `learning.EvaluationTelemetry` | Create | `time_on_task_seconds = delta_seconds`; `clicks` hard-coded to 0. |
| 7 | `assessments.QuizAttempt` | Update | `adaptive_plan` JSONField persisted with either AxiomEngine `PlanResponse` or `{"plan": [], "fallback": true}`. |
| 8 | `assessments.ProctoringLog` | Bulk create | Only when the proctoring endpoint is invoked (currently not from the Angular SPA). |

## Technical Notes

- The adaptive-plan stage operationalizes graph-aware pedagogical sequencing and LLM-assisted personalization by combining local graph extraction with prerequisite ordering before content generation (Wu et al., 2026).
- Parallel BAML invocation per failed concept produces structured RAG-style feedback objects (priority, explanation, prerequisite chain, modality-typed resources) rather than free-form LLM text, which keeps the surface predictable for downstream timeline rendering (Okonkwo et al., 2026).
- `vark_profile` is forwarded to AxiomEngine in every request and biases resource selection by modality, so the VARK onboarding outcome (CU-02) directly shapes adaptive-plan content (Alharbi et al., 2025).
- Angular submits the `student_id` from `sessionStore.userId()` (extracted from the JWT). Server-side, `AttemptViewSet.create` does not enforce equality with `request.user.id`; the responsibility for passing the correct identity is on the client. A hardening pass would force `student = request.user.id` at the view boundary.
- `final_score` stores the raw correct-count, not a percentage. Certificate eligibility (CU-13) compares `final_score >= 60.00` directly, so passing through quiz score alone requires a quiz with at least 60 questions unless `Evaluation.score` (which is also raw correct count) is normalized upstream.
- The `adaptive_plan` envelope is heterogeneous: success returns `{ student_id, course_id, items[], _meta }`; fallback returns `{ plan: [], fallback: true }`. Angular branches via `isAdaptivePlanResponse` / `isAdaptivePlanFallback` type guards. The server never reshapes the success envelope into the fallback shape.
- The Go side enforces three concurrency-relevant limits: 50 requests/minute per IP at the Fiber sliding-window limiter, a 20-second per-request deadline at the handler, and a 15-second per-LLM-call deadline inside the BAML fan-out. Circuit-breaker thresholds are 3 consecutive failures, 15-second open hold, 30-second closed window, 2 half-open probes (`internal/service/reasoning.go:62-78`).
- Proctoring detection is a documented integrity layer in this product family — face presence, multi-face detection, and tab switching are the three event types accepted by `ProctoringLog.EventType` and the integrity rationale follows multi-layered cheating-mitigation patterns (Corrigan-Gibbs et al., 2025). The Angular SPA in this repository does not implement proctoring capture, so end-to-end integrity coverage currently depends on operational telemetry through other channels (e.g., the bash test script).
- The orchestrator's 4-second polling cadence is hard-coded; it does not back off and does not stop until `diagnosticStatus` leaves `{pending, fallback}`. For a long-running async job the loop continues indefinitely — there is no max-attempts guard. [verify: no `maxRetries` constant in the orchestrator effect.]

## Request / Response

`POST /api/v1/attempts/` — HTTP 201

Request:

```json
{
  "quiz_id": 7,
  "student_id": 2,
  "answers": [
    { "question_id": 101, "selected_choice_id": 1001 },
    { "question_id": 102, "selected_choice_id": 1010 }
  ]
}
```

Success response (AxiomEngine OK):

```json
{
  "id": 42,
  "student": 2,
  "quiz": 7,
  "start_time": "2026-04-25T17:00:00Z",
  "end_time": "2026-04-25T17:14:36Z",
  "final_score": "1.00",
  "is_submitted": true,
  "adaptive_plan": {
    "student_id": "2",
    "course_id": "CS-301",
    "items": [
      {
        "topic": "Polymorphism",
        "priority": 1,
        "prerequisite_chain": ["Classes", "Inheritance"],
        "explanation": "...",
        "resources": [
          { "title": "Polymorphism Visual Guide", "url": "https://example.org/polymorphism", "resource_type": "video" }
        ]
      }
    ],
    "_meta": {
      "subgraph_tuples": 12,
      "topics_processed": 1,
      "items_generated": 3,
      "items_after_validation": 2,
      "llm_latency_ms": 3200,
      "total_latency_ms": 3360
    }
  },
  "score": 1.0,
  "max_score": 2.0,
  "failed_concepts": ["Polymorphism"],
  "evaluation_id": 19
}
```

Fallback variant (still HTTP 201; AxiomEngine timeout/connection error or non-2xx):

```json
{
  "id": 42,
  "student": 2,
  "quiz": 7,
  "start_time": "2026-04-25T17:00:00Z",
  "end_time": "2026-04-25T17:14:36Z",
  "final_score": "1.00",
  "is_submitted": true,
  "adaptive_plan": { "plan": [], "fallback": true },
  "score": 1.0,
  "max_score": 2.0,
  "failed_concepts": ["Polymorphism"],
  "evaluation_id": 19
}
```

`POST /api/v1/proctoring/logs/` — HTTP 201 (server-side; not exercised by the SPA)

Request:

```json
{
  "events": [
    {
      "attempt": 42,
      "event_type": "tab_switched",
      "timestamp": "2026-04-25T17:01:12Z",
      "severity_score": "0.85"
    },
    {
      "attempt": 42,
      "event_type": "multiple_faces",
      "timestamp": "2026-04-25T17:02:40Z",
      "severity_score": "0.95"
    }
  ]
}
```

Response:

```json
{ "ingested": 2 }
```
