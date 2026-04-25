# CU-12 — Consultar grafo cognitivo del estudiante

## Overview

A tutor (or any frontend caller with network reach) requests a cognitive-state graph for a single student by listing the failed concepts and optionally a target topic to anchor the subgraph. Angular sends the request **directly to AxiomEngine on port 8080**, bypassing Django entirely — `ReasoningApiService` uses the dedicated `AxiomApiClient` whose `baseUrlInterceptor` routes to `environment.axiomApiUrl`. The Go service classifies every connected node as `failed`, `learning`, or `mastered` and returns a Cytoscape/D3-shaped `{ nodes[], edges[] }` payload. The current Angular SPA renders this as a hierarchical PrimeNG TreeTable rather than a graph canvas, although `cytoscape` is listed as a dependency.

## Actors and Preconditions

- Actor: Tutor (intended consumer; no role enforcement at the Go layer).
- Angular has network access to `environment.axiomApiUrl` (typically `http://localhost:8080` in development, an HTTPS URL in production).
- The caller supplies a non-empty `student_id` and a non-empty `topics` query parameter (comma-separated concept IDs).
- For meaningful classification, the topics should match node names in AxiomEngine's in-memory knowledge graph (currently 19 hardcoded triples in `axiom-reasoning-svc/internal/graph/memory.go:241-264`).

## Frontend Entry Point

- Route: `/tutor` → `TutorDashboardPageComponent` ([src/app/pages/tutor/dashboard-page/tutor-dashboard-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/tutor/dashboard-page/tutor-dashboard-page.component.ts)). The cognitive-graph form lives in the left column of the dashboard.
- Form group: `graphForm = fb.group({ studentId: ['', Validators.required], topics: [[], Validators.required], targetTopic: [''] })`. The page constructor's effect (lines 106-118) auto-populates `topics` from `courseStore.selectedCourseDashboard()?.top_failed_concepts` (CU-11).
- Trigger: "Generate Graph" button calls `loadGraph()` after validating the form.
- Render component: `CognitiveShadowComponent` ([src/app/features/reasoning/cognitive-shadow/cognitive-shadow.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/reasoning/cognitive-shadow/cognitive-shadow.component.ts)) — a presentation-only PrimeNG TreeTable; it converts the flat `{ nodes, edges }` envelope into a `TreeNode[]` hierarchy via `buildTree(graph)`.
- Diagnostic-orchestrator entry: when the orchestrator advances to `step='result'` and `showCognitiveShadow=true`, the effect at lines 130-146 calls `reasoningStore.loadCognitiveGraph(studentId, failedTopics)` automatically without tutor intervention.

## End-to-End Flow

1. Tutor either (a) waits for `TutorDashboardPageComponent`'s effect to seed `graphForm.topics` from the dashboard's `top_failed_concepts`, or (b) types/select topics manually in the PrimeNG MultiSelect, then types `studentId` and optionally a `targetTopic`.
2. Tutor clicks "Generate Graph". `loadGraph()` validates the form; on success it extracts `{ studentId, topics, targetTopic }` and calls `reasoningStore.loadCognitiveGraph(studentId, topics, targetTopic || undefined)`.
3. `ReasoningStore.loadCognitiveGraph` ([src/app/entities/reasoning/model/reasoning.store.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/reasoning/model/reasoning.store.ts)) sets `isLoadingGraph=true` and awaits `firstValueFrom(reasoningApi.getCognitiveGraph(studentId, topics, targetTopic))`.
4. `ReasoningApiService.getCognitiveGraph(studentId, topics, targetTopic?)` ([src/app/entities/reasoning/api/reasoning.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/reasoning/api/reasoning.api.ts)) calls `axiomApi.get<CognitiveGraphResponse>('/api/v1/tutor/student/${studentId}/cognitive-graph', { params: { topics: topics.join(','), target_topic: targetTopic } })`.
5. `AxiomApiClient.get` ([src/app/shared/api/axiom-api.client.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/api/axiom-api.client.ts)) sets `API_TARGET='axiom'` and defaults `SKIP_AUTH=true`, `SKIP_REFRESH=true` on the `HttpContext`.
6. `baseUrlInterceptor` sees `API_TARGET='axiom'` and prepends `environment.axiomApiUrl` (typically `http://localhost:8080`).
7. `authInterceptor` and `refreshTokenInterceptor` skip immediately because `API_TARGET!=='django'` and the skip flags are set.
8. The browser issues `GET ${axiomApiUrl}/api/v1/tutor/student/${studentId}/cognitive-graph?topics=Polymorphism,Recursion[&target_topic=...]`. **Django is not in the path.**
9. Fiber's sliding-window rate limiter (50 req/min/IP at `axiom-reasoning-svc/cmd/server/main.go:75-86`) admits the request.
10. Fiber routes to `Handler.handleCognitiveGraph` ([axiom-reasoning-svc/internal/api/handlers.go](../../../axiom-reasoning-svc/internal/api/handlers.go) lines 154-193).
11. The handler reads `student_id` from the path param, parses `topics` (comma-separated) and the optional `target_topic` query param, and validates that both required values are non-empty (HTTP 400 on missing input).
12. The handler invokes `graph.GenerateCognitiveShadow(studentID, topics, targetTopic)` ([axiom-reasoning-svc/internal/graph/memory.go](../../../axiom-reasoning-svc/internal/graph/memory.go) lines 188-235).
13. `GenerateCognitiveShadow`:
    - Builds `failedSet = set(topics)`.
    - Computes prerequisite chains via `GetPrerequisiteChain(topic)` (DFS post-order over `depends_on` and `is_a` edges) for every failed topic; everything in the chain that is not already in `failedSet` joins `learningSet`.
    - Picks BFS seeds: all failed topics, or only `target_topic` when provided.
    - Extracts a depth-1 local subgraph via `GetLocalSubgraph(seeds, depth=1)`, deduplicates edges, and keeps only nodes with at least one edge.
    - Classifies each connected node:
      - `failed` if in `failedSet`.
      - `learning` if in `learningSet` and not `failed`.
      - `mastered` otherwise.
14. The handler returns `CognitiveGraphResponse { nodes: VisualNode[], edges: VisualEdge[] }` (HTTP 200) where each `VisualNode = { id, label, cognitive_state }` and `VisualEdge = { source, target, relation }`.
15. Angular receives the envelope. `ReasoningStore` writes it into the `cognitiveGraph` signal and clears `isLoadingGraph`.
16. `<app-cognitive-shadow [graph]="reasoningStore.cognitiveGraph()" [isLoading]="reasoningStore.isLoadingGraph()" />` renders. Its `@Input() set graph` setter calls `buildTree(graph)` which folds the edges into a parent/child `TreeNode[]` and feeds the PrimeNG TreeTable.

## Angular Implementation

- `ReasoningApiService.getCognitiveGraph(studentId: string, topics: string[], targetTopic?: string): Observable<CognitiveGraphResponse>`. The method joins the `topics` array with commas before sending; it does not URL-encode commas (Django/Go parse them as-is).
- `ReasoningApiService` is the only service that uses `AxiomApiClient`. The other methods on the same class (`generateAdaptivePlan`) are not invoked from the Angular SPA in current flows — `runDiagnosticFromAttempt` and `applyAttemptResult` get plans through Django because Django wraps the AxiomEngine call (CU-09).
- Type: `CognitiveGraphResponse = { nodes: CognitiveGraphNode[]; edges: CognitiveGraphEdge[] }`. `CognitiveGraphNode = { id, label, cognitive_state: 'failed' | 'learning' | 'mastered' }`. `CognitiveGraphEdge = { source, target, relation }`. (See [src/app/entities/reasoning/model/reasoning.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/reasoning/model/reasoning.types.ts).)
- `ReasoningStore.loadCognitiveGraph(studentId, topics, targetTopic?)`:
  - `patchState({ isLoadingGraph: true, error: null })`.
  - `firstValueFrom(reasoningApi.getCognitiveGraph(...))` then `patchState({ cognitiveGraph: response, isLoadingGraph: false })`.
  - On error patches `error` and clears `isLoadingGraph`.
- `CognitiveShadowComponent`:
  - Inputs: `set graph(value: CognitiveGraphResponse | null)` (immediately runs `buildTree` and stores into `_graph`), `@Input() isLoading = false`.
  - `buildTree(graph)`: builds a `Map<id, TreeNode>` from `nodes`, links each `edge.source` as a child of `edge.target`, then returns the roots (nodes that never appear as a `source`).
  - Template: PrimeNG TreeTable showing `node.label` (with id) and a colored badge for `cognitive_state` (mastered=green, learning=amber, failed=red). Skeleton on `isLoading()`. Empty state when `graph()` is null.
- The `cytoscape` package is listed in [package.json](D:/Repositories/angular/core-lms-frontend/package.json) but is not imported anywhere in `src/app/`. [verify: searched for `import cytoscape` and `from 'cytoscape'`; no matches.] The current rendering choice is the TreeTable.
- Errors land in `reasoningStore.error()`; the dashboard template renders the message inline below the form.

## Backend Implementation

- This use case has no Django backend. The Angular SPA calls AxiomEngine directly.
- AxiomEngine endpoint: `GET /api/v1/tutor/student/:student_id/cognitive-graph?topics=...&target_topic=...` (port 8080 by default).
- Handler: `Handler.handleCognitiveGraph` at `axiom-reasoning-svc/internal/api/handlers.go:154-193`.
- Validation: `student_id` (path) and `topics` (query) required; missing either returns HTTP 400 `{ "error": "validation_error", "details": "..." }`.
- Service: `graph.InMemoryGraph.GenerateCognitiveShadow(studentID, topics, targetTopic)` at `axiom-reasoning-svc/internal/graph/memory.go:188-235`.
- Underlying data: 19 hardcoded `(source, relation, target)` triples loaded from `defaultTuples()` at `internal/graph/memory.go:241-264`. Relations are `depends_on` and `is_a`.
- No database; no persistence. The graph is process-local in-memory only.
- Status codes: 200 on success, 400 on missing/empty inputs, 429 if the Fiber sliding-window limiter trips, 500 on graph traversal failure (rare; the in-memory graph has no I/O).

## Data Model Involvement

| Layer | Entity | Operation | Notes |
|---|---|---|---|
| Go DTO | `domain.CognitiveGraphResponse` | Construct | Returned to the client; built in the handler. |
| Go DTO | `domain.VisualNode` | Construct | `{ id, label, cognitive_state }`. |
| Go DTO | `domain.VisualEdge` | Construct | `{ source, target, relation }`. |
| Go in-memory graph | `graph.InMemoryGraph` | Read | Traversal over `forward`/`reverse` adjacency maps; no DB. |

## Technical Notes

- This endpoint deliberately bypasses Django: it carries no JWT, no Django-side authorization, and no Django-side audit. Network-layer trust (private VPC, CORS allowlist, optional service-mesh policies) is the only access control. Production deployments should ensure `axiomApiUrl` is reachable only from authorized origins.
- The classification does not query Django's `Evaluation`, `FailedTopic`, or `QuizAttempt` tables — it relies purely on caller-supplied `topics` plus the in-memory prerequisite topology. This keeps the endpoint stateless and fast, but it also means the graph reflects what the tutor *says* failed, not what the database records (Wu et al., 2026).
- The CV-01 contract violation (VARK enum mismatch: Django uses `aural`, Go expects `auditory`) does not affect this endpoint — VARK is not part of the cognitive-graph request — but it does affect CU-09's adaptive-plan path.
- The current `cognitive_state` taxonomy (`failed`, `learning`, `mastered`) is graph-visualization-friendly and can be rendered with any of the libraries present in the dependency tree; the choice of PrimeNG TreeTable in the SPA is a presentation decision, not a backend constraint.
- The `target_topic` query parameter narrows the BFS seeds to a single failed concept, which is useful when a tutor wants to focus on one concept's prerequisite chain instead of the union of all failed concepts; it is optional.
- The classification scheme intentionally projects mastery (everything connected but not in the failed/learning set is "mastered") — the in-memory graph does not have ground-truth mastery records, so this is a presentation heuristic, not a measurement. Tutors should interpret `mastered` as "structurally adjacent and not flagged" rather than "tested and passed".
- Graph-based prerequisite contextualization aligns with adaptive-learning workflows that prioritize structural concept dependencies for personalized remediation (Wu et al., 2026); the same principle drives the prerequisite-chain stage of the CU-09 adaptive plan.

## Request / Response

`GET ${axiomApiUrl}/api/v1/tutor/student/2/cognitive-graph?topics=Polymorphism,Recursion` — HTTP 200

Response:

```json
{
  "nodes": [
    { "id": "Polymorphism", "label": "Polymorphism", "cognitive_state": "failed" },
    { "id": "Inheritance", "label": "Inheritance", "cognitive_state": "learning" },
    { "id": "Classes", "label": "Classes", "cognitive_state": "learning" },
    { "id": "Objects", "label": "Objects", "cognitive_state": "mastered" }
  ],
  "edges": [
    { "source": "Polymorphism", "target": "Inheritance", "relation": "depends_on" },
    { "source": "Inheritance", "target": "Classes", "relation": "depends_on" },
    { "source": "Classes", "target": "Objects", "relation": "depends_on" }
  ]
}
```

`GET ${axiomApiUrl}/api/v1/tutor/student/2/cognitive-graph?topics=Polymorphism&target_topic=Polymorphism` — HTTP 200 (narrowed seed)

Response: same shape, narrowed to the local subgraph around `Polymorphism`.

Validation error (HTTP 400, missing `topics`):

```json
{ "error": "validation_error", "details": "topics query parameter is required" }
```

Rate-limit overflow (HTTP 429):

```json
{ "error": "rate_limit_exceeded", "details": "Too many requests. Max 50 per minute." }
```
