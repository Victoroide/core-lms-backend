# CU-01 — Gestionar sesión (login + refresh JWT)

## Overview

A student or tutor exchanges credentials for a JWT access/refresh pair, then transparently rotates the access token on expiry through a queueing refresh interceptor. The Angular SPA stores both tokens plus minimal user metadata in `localStorage`, attaches the access token to every Django call, and rebroadcasts the refreshed token across in-flight requests. Login establishes the session signal that gates every other use case.

## Actors and Preconditions

- Actors: Student, Tutor.
- A `LMSUser` row exists in `apps/learning/models/user_model.py` with the submitted credentials.
- Angular can reach the Django API at `environment.djangoApiUrl`.
- No prior session is required to visit `/login`; the `authGuard` actively redirects authenticated users away from protected routes only.

## Frontend Entry Point

- Route: `/login` declared in [src/app/app.routes.ts](D:/Repositories/angular/core-lms-frontend/src/app/app.routes.ts) (no guard).
- Component: `LoginPageComponent` at [src/app/pages/auth/login-page/login-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/auth/login-page/login-page.component.ts), which embeds `<app-login-form />`.
- Trigger: form submit handler on `LoginFormComponent` ([src/app/features/auth/login-form/login-form.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/auth/login-form/login-form.component.ts)).
- Token refresh has no entry point — it runs inside `refreshTokenInterceptor` whenever any HTTP call returns 401 ([src/app/shared/api/interceptors/refresh-token.interceptor.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/api/interceptors/refresh-token.interceptor.ts)).

## End-to-End Flow

1. Angular `LoginFormComponent.submit()` validates the reactive form (`username`, `password`, `role` controls) and calls `sessionStore.login({ username, password, preferredRole })`.
2. `SessionStore.login` (signal store at [src/app/entities/session/model/session.store.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/session/model/session.store.ts)) sets `isLoading=true`, then calls `authApi.login(payload)` via `firstValueFrom`.
3. `AuthApiService.login` ([src/app/entities/session/api/auth.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/session/api/auth.api.ts)) invokes `djangoApi.post<TokenPairResponse>('/api/v1/auth/token/', payload, { skipAuth: true, skipRefresh: true })`.
4. `baseUrlInterceptor` prepends `environment.djangoApiUrl` because the request `API_TARGET` context token is `'django'` ([src/app/shared/api/interceptors/base-url.interceptor.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/api/interceptors/base-url.interceptor.ts)).
5. `authInterceptor` and `refreshTokenInterceptor` are both bypassed because `SKIP_AUTH=true` and `SKIP_REFRESH=true`.
6. Django routes `POST /api/v1/auth/token/` through `core_lms/urls.py:35-37` to `RateLimitedTokenView.post` (`apps/learning/viewsets/auth_viewset.py`).
7. `@ratelimit(key="ip", rate="10/m", method="POST", block=False)` runs first; if the IP is over the threshold the view returns HTTP 429 `{"detail": "Too many login attempts. Try again later."}`.
8. Otherwise SimpleJWT's `TokenObtainPairView` runs with `AxiomTokenObtainPairSerializer` (`apps/learning/serializers/token_serializer.py`), which embeds `role`, `vark_dominant`, and `user_id` in the JWT and appends a `user` envelope to the response.
9. Angular receives `{ access, refresh, user }`. `SessionStore.login` calls `extractJwtPayload(access)` ([src/app/shared/lib/auth/jwt.utils.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/lib/auth/jwt.utils.ts)) to read `role` and `user_id`, and writes every key under the `axiomlms.*` prefix in `localStorage` (see [src/app/shared/config/api.config.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/config/api.config.ts)).
10. `patchState` updates the store signals (`accessToken`, `refreshToken`, `activeRole`, `userId`, `username`, `dominantVark`); the computed signal `isAuthenticated` flips to true and `LoginFormComponent.submit()` calls `router.navigate(['/tutor'])` or `router.navigate(['/student'])` based on the chosen role.
11. On any subsequent Django call, `authInterceptor` reads `sessionStore.accessToken()` and clones the request with `Authorization: Bearer ${accessToken}`.
12. When Django responds 401 to a non-auth request, `refreshTokenInterceptor` calls `getOrCreateRefreshStream()`, which posts `POST /api/v1/auth/token/refresh/` exactly once even if multiple requests fail concurrently (singleton via `shareReplay(1)` on `refreshInFlight$`).
13. `TaggedTokenRefreshView.post` (`apps/learning/viewsets/auth_viewset.py`) delegates to SimpleJWT's `TokenRefreshView`, blacklists the old refresh token (`BLACKLIST_AFTER_ROTATION=True`), and returns a new `{ access, refresh }` pair.
14. The interceptor calls `sessionStore.updateAccessToken(newAccessToken)` and replays the original request with the new bearer token plus `SKIP_REFRESH=true` to prevent infinite loops; if the refresh fails, `sessionStore.logout()` clears storage and routes to `/login`.

## Angular Implementation

- `AuthApiService.login(payload: LoginRequest): Observable<TokenPairResponse>` — POST to `/api/v1/auth/token/` with `{ skipAuth: true, skipRefresh: true }` options.
- `AuthApiService.refreshToken(refresh: string): Observable<RefreshTokenResponse>` — POST to `/api/v1/auth/token/refresh/` with the same skip flags.
- `SessionStore` (signal store, `providedIn: 'root'`) state: `accessToken`, `refreshToken`, `activeRole: 'STUDENT' | 'TUTOR' | null`, `username`, `userId`, `dominantVark`, `isLoading`, `error`. Computed: `isAuthenticated`.
- `SessionStore.login(credentials)` returns `Promise<boolean>` (`true` on success). It is awaited by the component, not subscribed via `async` pipe.
- `SessionStore.hydrate()` reads every `axiomlms.*` key from `localStorage` and rebuilds state on app boot (must be called explicitly during component initialization).
- `LoginFormComponent` form: `FormBuilder` group with `username: ['', Validators.required]`, `password: ['', Validators.required]`, `role: ['STUDENT', Validators.required]`. The component reads `sessionStore.isLoading()` and `sessionStore.error()` for UI feedback.
- `authInterceptor` is a `HttpInterceptorFn` that injects `SessionStore` and reads `accessToken()` reactively; it skips when `SKIP_AUTH=true` or `API_TARGET!=='django'`.
- `refreshTokenInterceptor` queues parallel 401s through a module-scoped `refreshInFlight$: Observable<string | null>` so a single refresh call satisfies every pending request; on success the cached observable replays the new access token, on failure it calls `sessionStore.logout()`.
- Errors surface from `authApi.login` as `HttpErrorResponse`; `SessionStore.login` catches them, writes a localized message into the `error` signal, and re-throws-as-false to the component. `apiErrorInterceptor` only logs to `console.error` and does not raise toasts ([src/app/shared/api/interceptors/api-error.interceptor.ts](D:/Repositories/angular/core-lms-frontend/src/app/shared/api/interceptors/api-error.interceptor.ts)).

## Backend Implementation

- Endpoints: `POST /api/v1/auth/token/` and `POST /api/v1/auth/token/refresh/`, registered directly in [core_lms/urls.py](../../core_lms/urls.py) lines 35-42 (not via DRF router).
- Views: `RateLimitedTokenView.post` and `TaggedTokenRefreshView.post` in [apps/learning/viewsets/auth_viewset.py](../../apps/learning/viewsets/auth_viewset.py) — both AllowAny.
- Serializers: `AxiomTokenObtainPairSerializer` (extends `TokenObtainPairSerializer`) at `apps/learning/serializers/token_serializer.py` — overrides `get_token` and `validate` to enrich claims and the response envelope.
- Service: none; SimpleJWT (`rest_framework_simplejwt`) handles credential validation, token issuance, and blacklist enforcement.
- Models read: `learning.LMSUser` (credential validation), `token_blacklist.OutstandingToken`, `token_blacklist.BlacklistedToken` (rotation tracking).
- Permissions: `AllowAny` on both endpoints; downstream protected endpoints rely on DRF default `IsAuthenticated` plus the role-specific classes in `apps/learning/permissions.py`.
- Status codes: 200 on success, 401 on bad credentials or invalid/expired refresh, 429 on rate-limit overflow.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `learning.LMSUser` | Read | Credential validation; `role`, `vark_dominant`, `user_id` flow into custom JWT claims. |
| `token_blacklist.OutstandingToken` | Write | SimpleJWT records each refresh on issuance. |
| `token_blacklist.BlacklistedToken` | Write | `BLACKLIST_AFTER_ROTATION=True` causes the previously used refresh token to be blacklisted on every rotation. |

## Technical Notes

- Access token lifetime is `timedelta(minutes=30)` and refresh lifetime is `timedelta(days=7)` per `SIMPLE_JWT` in `core_lms/settings.py:134-135`. The frontend never inspects expiry; it relies on Django returning 401 to trigger refresh.
- The login response includes the user envelope so the SPA initializes role-aware navigation without a separate profile call, supporting the role-conditional VARK onboarding gate (Alharbi et al., 2025).
- `refreshTokenInterceptor` collapses parallel 401s through `shareReplay(1)`, avoiding the race where N concurrent failed requests each post to `/auth/token/refresh/` and only one succeeds.
- The interceptor explicitly skips refresh when the failed URL contains `/api/v1/auth/token/`, preventing an infinite refresh-on-refresh loop.
- `sessionStore.logout()` clears every `axiomlms.*` key and calls `router.navigate(['/login'])`; it is invoked by both the explicit logout button in `AppShellComponent` and by the refresh failure path in the interceptor.
- Tokens are kept in `localStorage` rather than `HttpOnly` cookies; XSS exposure is therefore the dominant residual risk and must be mitigated upstream by the Angular template safety guarantees and CSP configuration.
- `IsStudent` and `IsTutor` (`apps/learning/permissions.py`) check `request.user.role` after JWT validation; the JWT-embedded `role` claim is for frontend convenience only and is not trusted on the server.

## Request / Response

`POST /api/v1/auth/token/` — HTTP 200

Request:

```json
{
  "username": "alice",
  "password": "demo_pass_2026"
}
```

Response:

```json
{
  "access": "<jwt_access>",
  "refresh": "<jwt_refresh>",
  "user": {
    "id": 2,
    "username": "alice",
    "email": "alice@example.com",
    "role": "STUDENT",
    "vark_dominant": "visual",
    "full_name": "Alice Doe"
  }
}
```

`POST /api/v1/auth/token/refresh/` — HTTP 200

Request:

```json
{ "refresh": "<jwt_refresh>" }
```

Response:

```json
{
  "access": "<new_jwt_access>",
  "refresh": "<new_jwt_refresh>"
}
```

Error envelope on rate-limit overflow (HTTP 429):

```json
{ "detail": "Too many login attempts. Try again later." }
```
