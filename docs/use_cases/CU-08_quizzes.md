# CU-08 — Consultar quizzes disponibles

## Overview

Anyone (anonymous or authenticated) browses available quizzes through the assessments app. Angular surfaces them in two places: as a per-course list inside the student/tutor course viewer, and as a dropdown in the diagnostic orchestrator that drives CU-09. Django's `QuizViewSet` is `AllowAny` for safe methods and filters out inactive quizzes for non-tutor callers, while the public `AnswerChoiceSerializer` strips `is_correct` so correctness leakage is impossible before submission.

## Actors and Preconditions

- Actors: Public user, Student, Tutor (any role can list and retrieve).
- No authentication is required for `GET /api/v1/quizzes/` and `GET /api/v1/quizzes/{id}/`.
- For non-tutor callers, only quizzes with `is_active=True` are returned. Tutors see every quiz including inactive ones.
- For meaningful detail, at least one `Question` with `AnswerChoice` rows must exist for the quiz.

## Frontend Entry Point

- Per-course list (student): `/student/course/:courseId` → `CourseViewerPageComponent` sidebar quiz section. The sidebar reads `courseStore.selectedCourseQuizzes()` (loaded by `loadCourseQuizzes(courseId)`) and shows each quiz with a "Start" button that calls `selectQuiz(quizId)`.
- Per-course list (tutor): `/tutor/course/:courseId` → `TutorCourseViewerPageComponent` mirrors the same sidebar; tutor side adds an "Edit" button that opens the quiz dialog (CU-08 also covers tutor authoring).
- Diagnostic orchestrator dropdown: any student dashboard (`/student`) → `<app-adaptive-plan-form />` → `<app-diagnostic-orchestrator />` ([src/app/features/reasoning/diagnostic-orchestrator/diagnostic-orchestrator.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/reasoning/diagnostic-orchestrator/diagnostic-orchestrator.component.ts)) → quiz selection dropdown bound to `quizStore.quizzes()`.
- Trigger: parent `CourseViewerPageComponent` constructor calls `quizStore.loadQuizzes()` (or, when scoped, `courseStore.loadCourseQuizzes(courseId)`); detail load fires `quizStore.loadQuizDetail(quizId)` on quiz click.
- Tutor authoring trigger: "New Evaluation" button on `TutorCourseViewerPageComponent` or `TutorDashboardPageComponent` opens a PrimeNG `<p-dialog>` and renders the `quizForm` reactive form group.

## End-to-End Flow

1. The page constructor calls `quizStore.loadQuizzes()` (or `courseStore.loadCourseQuizzes(courseId)`, which delegates to the same `QuizApiService.getQuizzes(courseId)`).
2. `QuizApiService.getQuizzes(courseId?)` ([src/app/entities/assessment/api/quiz.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/assessment/api/quiz.api.ts)) calls `djangoApi.get<PaginatedResponse<QuizListResponse>>('/api/v1/quizzes/', { params: { course } })` and `map`s `response.results`.
3. `baseUrlInterceptor` resolves the URL; `authInterceptor` attaches the bearer token if present (skipped silently when SKIP_AUTH-true paths run, but `getQuizzes` does not set that flag, so an authenticated session sends the token transparently — Django still serves the request as `AllowAny`).
4. Django routes `GET /api/v1/quizzes/` from `apps/assessments/urls.py` to `QuizViewSet.list` ([apps/assessments/viewsets/quiz_viewset.py](../../apps/assessments/viewsets/quiz_viewset.py)).
5. `QuizViewSet.get_permissions()` returns `[AllowAny()]` for `list / retrieve` and `[IsAuthenticated(), IsTutor()]` for `create / update / partial_update / destroy`.
6. `QuizViewSet.get_queryset()` starts from `Quiz.objects.all()` and applies `is_active=True` when the caller is unauthenticated or is not a tutor (`request.user.role != 'TUTOR'`).
7. If `?course=<id>` is present, the queryset is filtered by `course_id`.
8. `QuizListSerializer` returns `[id, title, course, time_limit_minutes, is_active, question_count]` (where `question_count` is a `SerializerMethodField` counting nested questions).
9. `QuizStore.loadQuizzes` writes the results into the `quizzes` signal; the sidebar UI iterates it and renders quiz cards.
10. On quiz click, `QuizApiService.getQuizDetail(quizId)` returns `QuizDetailResponse` from `GET /api/v1/quizzes/{id}/`.
11. Django dispatches to `QuizViewSet.retrieve`; the serializer chosen depends on caller role: `QuizDetailSerializer` for non-tutors (excludes `is_correct` on choices), `QuizTutorSerializer` for tutors (includes it).
12. `QuestionSerializer` returns `[id, text, concept_id, order, choices]`; nested `AnswerChoiceSerializer` returns `[id, text]` only for the public path.
13. `QuizStore.loadQuizDetail` writes `selectedQuizDetail` into the store; `CourseViewerPageComponent` reads it and renders `<app-quiz-player [quiz]="quizStore.selectedQuizDetail()!" />` (the player is the entry point for CU-09).
14. For tutor authoring, `QuizApiService.createQuiz(payload)` calls `POST /api/v1/quizzes/` with the form-builder body. Django routes through the same viewset; `IsAuthenticated + IsTutor` admit the call; DRF deserialization persists the quiz, questions, and choices.

## Angular Implementation

- `QuizApiService.getQuizzes(courseId?: number): Observable<QuizListResponse[]>` (extracts `.results`).
- `QuizApiService.getQuizDetail(quizId: number): Observable<QuizDetailResponse>`.
- `QuizApiService.createQuiz(payload: any): Observable<QuizDetailResponse>` — payload type is `any`; the tutor form sends nested `questions[].choices[]` matching the Django serializer expectations.
- `QuizApiService.deleteQuiz(quizId: number): Observable<void>`.
- Types ([src/app/entities/assessment/model/quiz.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/assessment/model/quiz.types.ts)):
  - `QuizListResponse = { id, title, course, time_limit_minutes, is_active, question_count }`.
  - `Question = { id, text, concept_id, order, choices }`; `AnswerChoice = { id, text }`.
  - `QuizDetailResponse = { id, title, description, course, time_limit_minutes, is_active, questions }`.
- `QuizStore` (signal store, `providedIn: 'root'`) state: `quizzes: QuizListResponse[]`, `selectedQuizDetail: QuizDetailResponse | null`, `isLoadingQuizzes`, `isLoadingDetail`, `error`. Methods: `loadQuizzes()`, `loadQuizDetail(quizId)`, `clearQuizDetail()`. Subscription: `firstValueFrom` then `patchState`.
- Tutor authoring form (in both `TutorCourseViewerPageComponent` and `TutorDashboardPageComponent`):

  ```ts
  quizForm = fb.group({
    title: ['', Validators.required],
    description: [''],
    timeLimit: [30, Validators.required],
    questions: fb.array<FormGroup>([])
  });
  ```

  Each question is `fb.group({ text, concept_id, order, choices: fb.array<FormGroup>([]) })`; each choice is `fb.group({ text, is_correct })`. `setCorrectChoice(qIdx, cIdx)` flips all sibling `is_correct` values to `false` so radio-button semantics apply.
- `DiagnosticOrchestratorComponent` consumes `quizStore.quizzes()` filtered by the currently selected course (computed signal `filteredQuizzes`). It uses `toSignal(form.get('quizId').valueChanges, { initialValue: null })` to react to dropdown changes and auto-load quiz detail.
- Errors land in `quizStore.error()`; the UI surfaces them inline and through `GlobalToastService` in the orchestrator.

## Backend Implementation

- Endpoint: `/api/v1/quizzes/` (DRF router prefix in `apps/assessments/urls.py`).
- Viewset: `QuizViewSet` at [apps/assessments/viewsets/quiz_viewset.py](../../apps/assessments/viewsets/quiz_viewset.py), a `ModelViewSet`.
- Permissions:
  - `list / retrieve` → `[AllowAny()]`.
  - `create / update / partial_update / destroy` → `[IsAuthenticated(), IsTutor()]`.
- Queryset: `Quiz.objects.all()` filtered by `is_active=True` for non-tutor callers; optional `?course=<id>` filter.
- Serializers (`apps/assessments/serializers/quiz_serializer.py`):
  - List: `QuizListSerializer` — `[id, title, course, time_limit_minutes, is_active, question_count]`.
  - Detail (non-tutor): `QuizDetailSerializer` — `[id, title, description, course, time_limit_minutes, is_active, questions]`. `questions[]` uses `QuestionSerializer`; `choices[]` uses `AnswerChoiceSerializer` with fields `[id, text]` only.
  - Detail (tutor): `QuizTutorSerializer` — same shape but choices include `is_correct`.
- Models touched: `assessments.Quiz` (read/write), `assessments.Question` (read/write), `assessments.AnswerChoice` (read/write).
- Status codes: 200 on read, 201 on create, 200 on update, 204 on destroy, 400 on validation, 403 on non-tutor mutation.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `assessments.Quiz` | Read / Write | Filtered by `is_active=True` for non-tutors. |
| `assessments.Question` | Read / Write | Nested under quiz detail/payload; `concept_id` must match a node in the AxiomEngine knowledge graph for CU-09 to extract a usable subgraph. |
| `assessments.AnswerChoice` | Read / Write | `is_correct` exposed only via tutor serializer. |

## Technical Notes

- The `is_correct` field is filtered out at the serializer layer rather than at the queryset; this avoids leaking correctness through any path that reuses `Quiz.objects.all()`. Tutor callers receive `QuizTutorSerializer` only when authenticated and `request.user.role == 'TUTOR'`.
- List responses are paginated by DRF's global `PageNumberPagination` with `PAGE_SIZE=20` (`core_lms/settings.py:115-118`); the Angular store flattens to `response.results` and discards `count / next / previous`. Pagination cursors are not currently exposed in the UI.
- Anonymous discovery is supported because `AllowAny` covers the read paths. The `authInterceptor` still adds the bearer token when present; Django ignores it for `AllowAny` actions.
- Quiz authoring is the only ontology-mutation surface present in the Angular SPA — `Career`/`Semester`/`Course` editing is admin-only (CU-03). The reactive form mirrors the Django serializer's nested write expectations exactly.
- Concepts referenced in `Question.concept_id` are the bridge to AxiomEngine; the field must match a node name in the in-memory graph (`axiom-reasoning-svc/internal/graph/memory.go`) for adaptive-plan generation to succeed in CU-09 (Wu et al., 2026).
- The orchestrator's quiz dropdown filters by `courseStore.selectedCourseId()`; if no course is selected the dropdown shows every quiz returned by the unfiltered store call. Empty selection therefore behaves as "global quiz catalog".

## Request / Response

`GET /api/v1/quizzes/?course=12` — HTTP 200 (paginated list)

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 7,
      "title": "OOP Diagnostic Quiz",
      "course": 12,
      "time_limit_minutes": 30,
      "is_active": true,
      "question_count": 10
    }
  ]
}
```

`GET /api/v1/quizzes/7/` — HTTP 200 (non-tutor detail; `is_correct` excluded)

```json
{
  "id": 7,
  "title": "OOP Diagnostic Quiz",
  "description": "Diagnostic assessment for object-oriented concepts",
  "course": 12,
  "time_limit_minutes": 30,
  "is_active": true,
  "questions": [
    {
      "id": 101,
      "text": "Which principle allows one interface with multiple implementations?",
      "concept_id": "Polymorphism",
      "order": 1,
      "choices": [
        { "id": 1001, "text": "Polymorphism" },
        { "id": 1002, "text": "Encapsulation" }
      ]
    }
  ]
}
```

`POST /api/v1/quizzes/` — HTTP 201 (tutor-only authoring)

Request:

```json
{
  "course": 12,
  "title": "OOP Diagnostic Quiz",
  "description": "...",
  "time_limit_minutes": 30,
  "is_active": true,
  "questions": [
    {
      "text": "...",
      "concept_id": "Polymorphism",
      "order": 1,
      "choices": [
        { "text": "Polymorphism", "is_correct": true },
        { "text": "Encapsulation", "is_correct": false }
      ]
    }
  ]
}
```

Response: the saved quiz via `QuizTutorSerializer` (mirrors the request, plus IDs for nested rows and `created_at`).
