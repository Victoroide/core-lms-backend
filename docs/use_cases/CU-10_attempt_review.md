# CU-10 — Revisar intentos propios de quiz

## Overview

A student returns to a previously submitted quiz attempt to inspect the score, the failed concepts, and any adaptive plan persisted at submission time. Angular reaches the attempt either through the diagnostic orchestrator's polling refresh path (`reasoningStore.refreshAttemptResult`) or through a direct GET; Django serves it through `AttemptViewSet.retrieve` scoped to `student=request.user`. The persisted `adaptive_plan` may be either the AxiomEngine `PlanResponse` envelope or the `{"plan": [], "fallback": true}` fallback; both are rendered transparently in `AdaptivePlanTimelineComponent`.

## Actors and Preconditions

- Actor: Student.
- The caller is authenticated with role `STUDENT`.
- At least one `QuizAttempt` row exists owned by `request.user` (created by CU-09).
- The student is reviewing only their own attempts; cross-student access returns HTTP 404.

## Frontend Entry Point

- Primary entry: `/student` → `StudentDashboardPageComponent` → `<app-adaptive-plan-form />` → `<app-diagnostic-orchestrator />` ([src/app/features/reasoning/diagnostic-orchestrator/diagnostic-orchestrator.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/reasoning/diagnostic-orchestrator/diagnostic-orchestrator.component.ts)) — when `step()` is `'result'`, the component renders `<app-adaptive-plan-timeline />` populated from `reasoningStore.adaptivePlan()` and `reasoningStore.lastAttemptId()`.
- Polling entry (async mode): the orchestrator's effect at lines 100-118 invokes `reasoningStore.refreshAttemptResult(attemptId, { silent: true })` on a 4-second cadence whenever `diagnosticStatus()` is `'pending'` or `'fallback'`. Each tick GETs `/api/v1/attempts/{id}/`.
- Manual review: there is no dedicated `/student/attempts` history page in this codebase. [verify: routes only expose `/student`, `/student/course/:courseId`, no `/attempts/*` route]. After redirect from `CourseViewerPageComponent.onQuizSubmitted` the URL becomes `/student?attemptId=<id>`, but the dashboard component reads the query parameter without rendering an "attempts list" — that surface is the diagnostic orchestrator's `result` step.
- Trigger: orchestrator transitions automatically when `reasoningStore.diagnosticStatus()` becomes `'success'` or `'fallback'`. The polling refresh is a side-effect of `diagnosticStatus()` being `'pending'`.

## End-to-End Flow

1. After submission (CU-09), `ReasoningStore.applyAttemptResult` writes `lastAttemptId`, `adaptivePlan`, and `diagnosticStatus` based on the response shape.
2. If `diagnosticStatus === 'pending'`, `DiagnosticOrchestratorComponent` starts the 4-second polling effect: each tick calls `reasoningStore.refreshAttemptResult(attemptId, { silent: true })`.
3. `ReasoningStore.refreshAttemptResult` calls `attemptApi.getAttempt(attemptId)` ([src/app/entities/assessment/api/attempt.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/assessment/api/attempt.api.ts)) which translates to `djangoApi.get<AttemptResultResponse>('/api/v1/attempts/${attemptId}/')`.
4. `baseUrlInterceptor` resolves the URL; `authInterceptor` attaches `Authorization: Bearer ${accessToken}`.
5. Django routes `GET /api/v1/attempts/{id}/` from `apps/assessments/urls.py` to `AttemptViewSet.retrieve` ([apps/assessments/viewsets/attempt_viewset.py](../../apps/assessments/viewsets/attempt_viewset.py) lines 232-250).
6. `AttemptViewSet.permission_classes = [IsAuthenticated, IsStudent]` blocks non-students.
7. The view executes `QuizAttempt.objects.get(pk=pk, student=request.user)`; if the attempt is owned by another student the view returns HTTP 404.
8. `AttemptResultSerializer` returns the persisted attempt: `[id, student, quiz, start_time, end_time, final_score, is_submitted, adaptive_plan, score?, max_score?, failed_concepts?, evaluation_id?]` (the optional aggregate fields are present when the row carries them; for stored attempts they are read directly from the columns).
9. The `adaptive_plan` field is returned exactly as persisted by `ScoringService` — either the AxiomEngine `PlanResponse` (`{ student_id, course_id, items[], _meta }`) or the fallback `{ plan: [], fallback: true }`.
10. Angular `ReasoningStore.applyAttemptResult(response)` re-runs the type-guard classification: `isAdaptivePlanResponse` flips `diagnosticStatus` to `'success'` and writes `adaptivePlan`; `isAdaptivePlanFallback` flips to `'fallback'`; `normalizeJobId` keeps the loop alive if the row is still pending in async mode.
11. The orchestrator's effect at lines 130-146 advances `step` to `'result'` and (when `showCognitiveShadow=true`) triggers `reasoningStore.loadCognitiveGraph(studentId, failedTopics)`.
12. `<app-adaptive-plan-timeline [items]="store.adaptivePlan()?.items ?? []" [llmLatencyMs]="store.adaptivePlan()?._meta?.llm_latency_ms ?? null" [lastAttemptId]="store.lastAttemptId()" />` renders the persisted plan; on fallback the timeline shows an empty state derived from `store.fallbackReason()`.

## Angular Implementation

- `AttemptApiService.getAttempt(attemptId: number): Observable<AttemptResultResponse>` — straight GET; no query parameters.
- Type: `AttemptResultResponse` ([src/app/entities/assessment/model/attempt.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/assessment/model/attempt.types.ts)) — `adaptive_plan: AttemptAdaptivePlanEnvelope`, the discriminated union covering success/fallback/pending/null.
- `ReasoningStore.refreshAttemptResult(attemptId, options?: { silent?: boolean })`:
  - `silent=true` suppresses the toast and the spinner; used by the polling loop.
  - Internally awaits `firstValueFrom(attemptApi.getAttempt(attemptId))` then calls `applyAttemptResult(response)`.
- `ReasoningStore.applyAttemptResult(attempt)`:
  - Type guard `isAdaptivePlanResponse` (checks for `items` and `_meta` in `adaptive_plan`).
  - Type guard `isAdaptivePlanFallback` (checks `fallback === true`).
  - `normalizeJobId` extracts a non-empty `job_id` for async-pending detection.
  - On success: `patchState(diagnosticStatus: 'success', adaptivePlan: response.adaptive_plan, lastAttemptId, fallbackReason: null)`.
  - On fallback: `patchState(diagnosticStatus: 'fallback', fallbackReason: ..., adaptivePlan: null)`.
  - On pending: `patchState(diagnosticStatus: 'pending', jobId: ...)` — keeps the polling loop alive.
- `AdaptivePlanTimelineComponent` ([src/app/features/reasoning/adaptive-plan-timeline/adaptive-plan-timeline.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/reasoning/adaptive-plan-timeline/adaptive-plan-timeline.component.ts)) is pure presentation:
  - Inputs: `items: AdaptivePlanItem[]`, `isLoading`, `status`, `llmLatencyMs`, `lastAttemptId`.
  - Renders a PrimeNG Timeline (alternate layout); each item shows priority, topic, explanation, prerequisite chain, and resource icons.
  - `resourceIcon(type)` maps the resource type string to an emoji; resource cards are clickable links to `resource.url`.
- The list endpoint `GET /api/v1/attempts/` is wired server-side but Angular does not call it in the current code path — the SPA always reviews a single attempt via `lastAttemptId`. [verify: no `getAttempts()` method on `AttemptApiService`].

## Backend Implementation

- Endpoint: `GET /api/v1/attempts/{id}/` (and `GET /api/v1/attempts/` for the list path, exposed but not consumed by Angular).
- Viewset: `AttemptViewSet` (`viewsets.ViewSet`) at [apps/assessments/viewsets/attempt_viewset.py](../../apps/assessments/viewsets/attempt_viewset.py).
- Permissions: class-level `[IsAuthenticated, IsStudent]`.
- Methods:
  - `list` (lines 197-215): `QuizAttempt.objects.filter(student=request.user).order_by('-start_time')`, paginated by `PageNumberPagination`, serialized by `AttemptResultSerializer`.
  - `retrieve` (lines 232-250): `QuizAttempt.objects.get(pk=pk, student=request.user)`; 404 if non-owned.
- Serializer: `AttemptResultSerializer` (`apps/assessments/serializers/attempt_serializer.py`).
- Models touched: `assessments.QuizAttempt` (read with student-scoped queryset).
- Status codes: 200 on read, 401 on missing JWT, 403 on non-student, 404 on non-owned attempt.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `assessments.QuizAttempt` | Read | Student-scoped retrieval; `adaptive_plan` JSONField returned exactly as persisted by `ScoringService`. |

## Technical Notes

- Ownership is enforced at the queryset level (`student=request.user`), not via permission class. Cross-student access deterministically returns HTTP 404, not 403, because the queryset filters before `get_object()`.
- The `adaptive_plan` JSON envelope is heterogeneous (success vs. fallback); the SPA uses TypeScript discriminated-union type guards rather than schema validation. This contract violation is documented as CV-02 in [04_architecture.md](../04_architecture.md).
- The 4-second polling loop in `DiagnosticOrchestratorComponent` issues one GET per cycle and does not cancel in-flight requests; with a high backoff or stuck job the loop continues until `diagnosticStatus()` leaves `{pending, fallback}`. There is no max-attempts guard.
- `AdaptivePlanTimelineComponent.llmLatencyMs` exposes the AxiomEngine pipeline's `_meta.llm_latency_ms`, surfacing the LLM-side cost at review time. This makes the LLM contribution observable per attempt rather than only in aggregate analytics, consistent with RAG-grounded feedback observability patterns (Okonkwo et al., 2026).
- Reviewing previously generated plans uses the persisted graph subgraph implicitly — the rendered prerequisite chain comes from AxiomEngine's topological sort step, allowing the student to revisit the prerequisite ordering without recomputing it (Wu et al., 2026).
- Attempt review does not regenerate plans; the attempt's `adaptive_plan` is final once persisted. If AxiomEngine is upgraded, prior attempts continue to display the older payload shape verbatim.
- The list endpoint is paginated with `PAGE_SIZE=20` and ordered by `-start_time`, so a future "attempts history" page would load most-recent first; the current SPA does not surface this list anywhere.

## Request / Response

`GET /api/v1/attempts/42/` — HTTP 200 (success envelope persisted)

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
  }
}
```

`GET /api/v1/attempts/42/` — HTTP 200 (fallback envelope persisted)

```json
{
  "id": 42,
  "student": 2,
  "quiz": 7,
  "start_time": "2026-04-25T17:00:00Z",
  "end_time": "2026-04-25T17:14:36Z",
  "final_score": "1.00",
  "is_submitted": true,
  "adaptive_plan": { "plan": [], "fallback": true }
}
```

`GET /api/v1/attempts/` — HTTP 200 (paginated list; not consumed by Angular)

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "student": 2,
      "quiz": 7,
      "start_time": "2026-04-25T17:00:00Z",
      "end_time": "2026-04-25T17:14:36Z",
      "final_score": "1.00",
      "is_submitted": true,
      "adaptive_plan": { "plan": [], "fallback": true }
    }
  ]
}
```

Cross-student access (HTTP 404):

```json
{ "detail": "Not found." }
```
