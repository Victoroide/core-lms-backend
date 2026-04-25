# CU-02 — Completar onboarding VARK

## Overview

A newly authenticated student rates four learning-style modalities on a 0-10 scale; Django aggregates the answers, computes the dominant modality, and persists it as `LMSUser.vark_dominant`. The Angular SPA renders the questionnaire as a modal that auto-opens when the session has a user but no recorded VARK profile, blocking the rest of the dashboard until the modality is set. The persisted value is later forwarded to AxiomEngine as `vark_profile` so adaptive plans favor modality-matched resources.

## Actors and Preconditions

- Actor: Student.
- The caller is authenticated (`sessionStore.accessToken()` non-null) and has reached `/student`.
- `LMSUser.vark_dominant` for the caller is empty/null on the server (the modal trigger condition is `!sessionStore.dominantVark()` on the client side).
- The student is updating their own row — the path parameter `{id}` must equal `request.user.pk` server-side.

## Frontend Entry Point

- Route: `/student` declared in [src/app/app.routes.ts](D:/Repositories/angular/core-lms-frontend/src/app/app.routes.ts), protected by `authGuard` and `roleGuard` (data: `{ role: 'STUDENT' }`).
- Page component: `StudentDashboardPageComponent` ([src/app/pages/student/dashboard-page/student-dashboard-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/student/dashboard-page/student-dashboard-page.component.ts)) renders `<app-onboarding-modal />` at the bottom.
- Modal component: `OnboardingModalComponent` ([src/app/features/user/onboarding-modal/onboarding-modal.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/user/onboarding-modal/onboarding-modal.component.ts)).
- Trigger: the computed signal `visible` returns `true` whenever `!!sessionStore.userId() && !sessionStore.dominantVark()`. The PrimeNG `<p-dialog [visible]="visible()" [closable]="false" [modal]="true">` opens automatically; there is no explicit user click.
- Submit: button labeled "Complete Profile" calls `OnboardingModalComponent.submitAnswers()`.

## End-to-End Flow

1. After login, `StudentDashboardPageComponent` mounts and `OnboardingModalComponent` evaluates its `visible` computed signal.
2. The dialog opens; four PrimeNG `p-slider` controls are bound to instance fields `visualScore=5`, `auralScore=5`, `readWriteScore=5`, `kinestheticScore=5` (each scale 0-10).
3. The student adjusts sliders and clicks "Complete Profile"; `submitAnswers()` sets `isSubmitting.set(true)` and assembles the payload `{ answers: [{category, value}, ...] }` with the four current values in fixed order.
4. The component reads `sessionStore.userId()`; if null, it sets an error and aborts.
5. `userApi.submitVarkOnboarding(userId, payload)` ([src/app/entities/user/api/user.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/user/api/user.api.ts)) calls `djangoApi.post<VarkOnboardingResponse>('/api/v1/users/${userId}/onboard/', payload)`.
6. `baseUrlInterceptor` prepends `environment.djangoApiUrl`; `authInterceptor` attaches `Authorization: Bearer ${accessToken}`.
7. Django routes the request from `apps/learning/urls.py` (router prefix `users`) to `UserViewSet.onboard` in [apps/learning/viewsets/user_onboarding_viewset.py](../../apps/learning/viewsets/user_onboarding_viewset.py).
8. `UserViewSet.permission_classes = [IsAuthenticated]` admits the request; `onboard` resolves `user = self.get_object()` from `LMSUser.objects.all()`.
9. The action returns HTTP 403 if `user.pk != request.user.pk`, blocking cross-user updates.
10. `VARKOnboardingSerializer` validates the body — `answers` is a list of `VARKAnswerSerializer` items where `category` must be one of `visual|aural|read_write|kinesthetic` and `value` is an integer 0..10.
11. The action aggregates `defaultdict(int)` totals per category, picks `max(scores, key=scores.get)`, assigns `user.vark_dominant`, and persists with `user.save(update_fields=["vark_dominant"])`.
12. Django returns `{ student_id, vark_scores, vark_dominant }` with HTTP 200.
13. The component awaits the promise; on success it calls `sessionStore.setDominantVark(response.vark_dominant)`, which writes both the `axiomlms.dominantVark` localStorage entry and the `dominantVark` signal.
14. The `visible` computed signal flips to `false`, the dialog closes, and the dashboard becomes interactive.

## Angular Implementation

- `UserApiService.submitVarkOnboarding(userId: number, payload: VarkOnboardingRequest): Observable<VarkOnboardingResponse>` — POST to `/api/v1/users/${userId}/onboard/`.
- Request type: `VarkOnboardingRequest = { answers: VarkAnswer[] }` where `VarkAnswer = { category: BackendVarkCategory; value: number }` and `BackendVarkCategory = 'visual' | 'aural' | 'read_write' | 'kinesthetic'`.
- Response type: `VarkOnboardingResponse = { student_id: number; vark_scores: Record<string, number>; vark_dominant: string }`.
- `OnboardingModalComponent` does not use a `FormGroup` — slider values are stored as plain instance properties initialized to 5.
- State signals: `isSubmitting = signal(false)`, `errorMessage = signal('')`, `visible = computed(() => !!sessionStore.userId() && !sessionStore.dominantVark())`.
- Subscription pattern: `submitAnswers()` is `async`; it awaits `firstValueFrom(userApi.submitVarkOnboarding(...))` directly (no store layer for this domain).
- Persistence: on success the component calls `sessionStore.setDominantVark(value)`, which writes `localStorage` and patches the signal — there is no `userStore` mediating this domain.
- Error handling: a try/catch in the component populates `errorMessage` and toggles `isSubmitting=false`; the dialog stays open on failure so the student can retry.

## Backend Implementation

- Endpoint: `POST /api/v1/users/{id}/onboard/`.
- Viewset: `UserViewSet` (extends `viewsets.GenericViewSet`) at [apps/learning/viewsets/user_onboarding_viewset.py](../../apps/learning/viewsets/user_onboarding_viewset.py) lines 87-160. Action: `@action(detail=True, methods=["post"], url_path="onboard")` → `onboard(self, request, pk=None)`.
- Permissions: class-level `IsAuthenticated` (lines 95). Identity match (`user.pk != request.user.pk → 403`) enforced inside the action body, not via a permission class.
- Serializers: `VARKOnboardingSerializer` and nested `VARKAnswerSerializer` at lines 13-21 of the same file. `VARKAnswerSerializer.value` uses `IntegerField(min_value=0, max_value=10)`.
- Service: none; logic inlined in the action — `defaultdict(int)`, `max(scores, key=scores.get)`, `user.save(update_fields=["vark_dominant"])`.
- Models: `learning.LMSUser` (read for ownership check; write for `vark_dominant` only).
- Status codes: 200 on success, 400 on invalid payload (missing `answers`, wrong category, value out of range), 403 on cross-user attempt, 401 if the access token is missing or invalid.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `learning.LMSUser` | Read | Loaded by PK; identity comparison against `request.user`. |
| `learning.LMSUser` | Update | Only `vark_dominant` is rewritten via `save(update_fields=...)`. |

## Technical Notes

- The dominant modality drives later adaptive-plan generation: `AxiomEngineClient.request_adaptive_plan` reads `evaluation.student.vark_dominant` and forwards it as `vark_profile` so AxiomEngine biases resource selection toward the student's modality (Alharbi et al., 2025).
- Ties between categories resolve to the first maximum encountered in dictionary insertion order, which in Python 3.7+ matches payload order; the slider UI sends categories in a fixed sequence (`visual, aural, read_write, kinesthetic`), so ties default to `visual`.
- VARK profile inference from explicit user input rather than behavioral heuristics keeps the diagnostic deterministic and auditable, matching the AI-personalization paradigm grounded in declarative VARK answers (Alharbi et al., 2025).
- The Angular store layer applies a separate translation when sending the profile to AxiomEngine: `backendToAxiomVark()` maps `aural → auditory` ([src/app/shared/lib/vark/vark.utils.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/lib/vark/vark.utils.ts)) because the Go service expects `auditory`. This translation is invisible to CU-02 itself but is documented as contract violation CV-01 in [04_architecture.md § 5](../04_architecture.md).
- The endpoint requires `IsAuthenticated` only — it does not require `IsStudent`. A tutor account hitting `/api/v1/users/{tutor_pk}/onboard/` would succeed for their own row.
- Once `vark_dominant` is non-empty, the modal will not reopen on subsequent visits because `OnboardingModalComponent.visible` evaluates to `false`. There is no Angular UI path to update the value later — re-onboarding requires admin or a new endpoint not yet exposed.

## Request / Response

`POST /api/v1/users/2/onboard/` — HTTP 200

Request:

```json
{
  "answers": [
    { "category": "visual", "value": 8 },
    { "category": "aural", "value": 3 },
    { "category": "read_write", "value": 5 },
    { "category": "kinesthetic", "value": 4 }
  ]
}
```

Response:

```json
{
  "student_id": 2,
  "vark_scores": {
    "visual": 8,
    "aural": 3,
    "read_write": 5,
    "kinesthetic": 4
  },
  "vark_dominant": "visual"
}
```

Error envelope on cross-user attempt (HTTP 403):

```json
{ "detail": "You can only update your own VARK profile." }
```
