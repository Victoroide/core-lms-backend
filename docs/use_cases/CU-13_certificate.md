# CU-13 — Generar certificado de curso aprobado

## Overview

A student requests a completion certificate for a course; Django verifies eligibility against passing evaluations or quiz attempts (`PASSING_SCORE = 60.00`), computes a SHA-256 `certificate_hash` from `f"{student_id}:{course_id}:{issued_at_iso}"`, and returns the persisted row idempotently. Angular triggers the call from the course-overview card; on success it routes to `/certificate/:hash`, a public route that anyone can use to verify the certificate without authentication. Both generation and verification are mediated by `CertificateApiService` and `CertificateStore`.

## Actors and Preconditions

- Actors: Student (generation), anyone with a hash (verification — public route).
- For generation: the caller is authenticated with role `STUDENT`; `request.body` includes `student_id` and `course_id`; the student/course rows exist; the student has at least one passing evaluation or quiz attempt (`score >= 60.00` or `final_score >= 60.00`).
- For verification: no authentication required; the hash is the only secret (and acts as a bearer token-like proof), so URLs containing it should not be embedded in third-party trackers or pasted into share-links carelessly.
- The caller must already know the student/course IDs; the SPA reads them from `sessionStore.userId()` and `courseStore.selectedCourseId()`.

## Frontend Entry Point

- Generation entry: `/student` or `/student/course/:courseId` → `<app-course-overview />` ([src/app/features/course/course-overview/course-overview.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/features/course/course-overview/course-overview.component.ts)). Each course card exposes a "Generate Certificate" action (visible only to students). `generateCertificate(courseId)` calls `certificateStore.generate(courseId, sessionStore.userId()!)`.
- Verification entry: `/certificate/:hash` → `CertificateViewerPageComponent` ([src/app/pages/public/certificate-viewer-page/certificate-viewer-page.component.ts](D:/Repositories/angular/core-lms-frontend/src/app/pages/public/certificate-viewer-page/certificate-viewer-page.component.ts)) — public route, no `authGuard`.
- Trigger:
  - Generation — explicit click on the "Generate Certificate" button in the course card; the result hash is appended to the path and `router.navigate(['/certificate', hash])` opens the viewer.
  - Verification — `CertificateViewerPageComponent.ngOnInit` reads `route.snapshot.paramMap.get('hash')` and calls `certificateStore.verify(hash)` immediately on mount.

## End-to-End Flow

### Generation

1. Student clicks "Generate Certificate" on a course card. `CourseOverviewComponent.generateCertificate(courseId)` reads `sessionStore.userId()` and dispatches `certificateStore.generate(courseId, studentId)`.
2. `CertificateStore.generate` ([src/app/entities/certificate/model/certificate.store.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/certificate/model/certificate.store.ts)) sets `isGenerating=true`, awaits `firstValueFrom(certificateApi.generateCertificate(courseId, studentId))`, and translates the response.
3. `CertificateApiService.generateCertificate(courseId, studentId)` ([src/app/entities/certificate/api/certificate.api.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/certificate/api/certificate.api.ts)) calls `djangoApi.post<CertificateGenerationResponse>('/api/v1/certificates/generate/', { course_id, student_id })`.
4. `baseUrlInterceptor` resolves `environment.djangoApiUrl`; `authInterceptor` attaches `Authorization: Bearer ${accessToken}`.
5. Django routes the request via `apps/learning/urls.py` to `CertificateViewSet.generate` ([apps/learning/viewsets/certificate_viewset.py](../../apps/learning/viewsets/certificate_viewset.py) lines 77-129).
6. `get_permissions()` returns `[IsAuthenticated(), IsStudent()]` for the generate action.
7. The action validates `student_id` and `course_id`; missing values return HTTP 400. Missing rows in `LMSUser` or `Course` return HTTP 400.
8. The action calls `CertificateGenerator.issue_certificate(student, course)` at [apps/learning/services/certification_service.py](../../apps/learning/services/certification_service.py).
9. `_verify_eligibility(student, course)`:
   - Checks `Evaluation.objects.filter(student=student, course=course, score__gte=Decimal("60.00")).exists()`.
   - Or checks `QuizAttempt.objects.filter(student=student, quiz__course=course, is_submitted=True, final_score__gte=Decimal("60.00")).exists()`.
   - If neither passes, raises `CertificateEligibilityError`. The view catches it and returns HTTP 403 `{"error": "ineligible", "detail": "No passing evaluation or quiz attempt found (minimum score: 60.00)."}`.
10. If a `Certificate(student, course)` already exists, the service returns it unchanged (idempotent).
11. Otherwise the service computes `certificate_hash = sha256(f"{student.id}:{course.id}:{issued_at_iso}").hexdigest()` and inserts a new `Certificate` row.
12. On a concurrent insert, the `(student, course)` `unique_together` raises `IntegrityError`; the service catches it and re-fetches the now-existing row.
13. The view returns HTTP 201 with `{ certificate_hash, issued_at, course_id, student_id }`.
14. Angular `CertificateStore.generate` reads the response, fires `GlobalToastService.success('Certificado emitido')`, and returns the hash. `CourseOverviewComponent.generateCertificate` then calls `router.navigate(['/certificate', hash])`.

### Verification

15. The route `/certificate/:hash` mounts `CertificateViewerPageComponent` (no `authGuard` — public).
16. `ngOnInit` reads the `hash` path param and calls `certificateStore.verify(hash)`.
17. `CertificateApiService.verifyCertificate(hash)` calls `djangoApi.get<CertificateVerifyResponse>('/api/v1/certificates/verify/${hash}/')`.
18. Django routes to a verify endpoint that returns `{ is_valid, hash, issued_at, student_name, course_name }`. [verify: the existing `CertificateViewSet` exposes `@action(detail=False, methods=['get'], url_path=r'verify/(?P<hash>[a-f0-9]+)')` per the architecture and API references; the frontend treats this endpoint as `AllowAny`.]
19. The component renders the certificate document (decorative borders, student/course names, issued date) and exposes a Print button (`window.print()`) and a Home button (`router.navigate(['/'])`).
20. Hash lookup misses return HTTP 404; the page renders a "certificate not found" state read from `certificateStore.error()`.

## Angular Implementation

- `CertificateApiService.generateCertificate(courseId: number, studentId: number): Observable<CertificateGenerationResponse>` — POST `/api/v1/certificates/generate/` with `{ course_id, student_id }`.
- `CertificateApiService.verifyCertificate(hash: string): Observable<CertificateVerifyResponse>` — GET `/api/v1/certificates/verify/${hash}/`.
- Types ([src/app/entities/certificate/model/certificate.types.ts](D:/Repositories/angular/core-lms-frontend/src/app/entities/certificate/model/certificate.types.ts)):
  - `CertificateGenerationResponse = { certificate_hash, issued_at, course_id, student_id }`.
  - `CertificateVerifyResponse = { is_valid, hash, issued_at, student_name, course_name }`.
- `CertificateStore` (signal store, `providedIn: 'root'`):
  - State: `isGenerating`, `isVerifying`, `verifiedCertificate`, `error`.
  - `generate(courseId, studentId): Promise<string | null>` — awaits the API, fires success or error toasts (it inspects `HttpErrorResponse.status === 403` to translate the eligibility failure into a localized Spanish message), returns the hash or `null`.
  - `verify(hash): Promise<void>` — awaits the API, writes into `verifiedCertificate`, sets `error` on failure.
  - `clearState()` — resets all signals to initial state.
- `CourseOverviewComponent`:
  - `generateCertificate(courseId)` is the imperative click handler; it awaits `certificateStore.generate(...)` and navigates on success.
  - The "Generate Certificate" button is rendered only for students (component reads `sessionStore.activeRole()`).
- `CertificateViewerPageComponent`:
  - Reads `hash` from `ActivatedRoute.snapshot.paramMap` in `ngOnInit`.
  - `printCertificate()` calls `window.print()`; the template has print-optimized CSS that hides buttons.
  - `goHome()` calls `router.navigate(['/'])`.
- Errors propagate through `certificateStore.error()` and `GlobalToastService`. The interceptor chain logs to console; the store layer is responsible for user-facing messages.

## Backend Implementation

- Endpoint (generate): `POST /api/v1/certificates/generate/` (action route on the certificates router).
- Endpoint (verify): `GET /api/v1/certificates/verify/{hash}/` (action route, `AllowAny`).
- Viewset: `CertificateViewSet` (`viewsets.ViewSet`) at [apps/learning/viewsets/certificate_viewset.py](../../apps/learning/viewsets/certificate_viewset.py).
- Permissions:
  - Generate action: `[IsAuthenticated, IsStudent]`.
  - Verify action: `[AllowAny]` (hash is the only credential).
- Service: `CertificateGenerator` at [apps/learning/services/certification_service.py](../../apps/learning/services/certification_service.py). Constants: `PASSING_SCORE = Decimal("60.00")` (line 25).
- Hash function: `sha256(f"{student_id}:{course_id}:{issued_at_iso}").hexdigest()` (lines 28-40).
- Models read: `learning.LMSUser`, `learning.Course`, `learning.Evaluation`, `assessments.QuizAttempt`.
- Models written: `learning.Certificate` (new row or idempotent return; `unique_together = (student, course)`).
- Status codes (generate): 201 on success (new or existing), 400 on missing payload or missing FK, 401 on missing JWT, 403 on non-student or `CertificateEligibilityError`, 500 on unexpected `IntegrityError` that the service cannot resolve.
- Status codes (verify): 200 on hash match, 404 on miss.

## Data Model Involvement

| Model | Operation | Notes |
|---|---|---|
| `learning.LMSUser` | Read | Student existence check; eligibility scope. |
| `learning.Course` | Read | Course existence check; certificate FK target. |
| `learning.Evaluation` | Read | Eligibility: `score >= 60.00`. |
| `assessments.QuizAttempt` | Read | Eligibility: `is_submitted=True` and `final_score >= 60.00`. |
| `learning.Certificate` | Read / Create | Idempotent issuance; `(student, course)` `unique_together`; `certificate_hash` is also DB-unique. |

## Technical Notes

- `PASSING_SCORE = Decimal("60.00")` is an absolute threshold compared against raw stored scores. `Evaluation.score` and `QuizAttempt.final_score` both store raw correct counts (not percentages), so a quiz with two questions yields a maximum `final_score` of 2.0 — well below 60.00. In practice, eligibility is realistic only on `Evaluation` rows seeded with already-normalized values, or on quizzes with at least 60 questions. This is a known scoring-semantics gap inherited from CU-09.
- Idempotence is implemented at two layers: the service does an explicit `Certificate.objects.get_or_none(student=student, course=course)` lookup, and the database `unique_together` enforces it as a hard constraint. Concurrent issuance requests are reconciled by catching `IntegrityError` and re-fetching the existing row.
- The hash carries the issuance timestamp, so even if a row were ever re-created (which the unique constraint prevents) the new hash would differ. Hash collisions would require a second-level constraint violation; the unique index on `certificate_hash` itself catches that as a fallback.
- The verify endpoint is `AllowAny` and uses the hash as the verification proof. There is no rate-limit on `/verify/`, so brute-force scans across the 64-character hex space remain computationally infeasible but a future hardening pass should add rate-limiting at the bucket policy or in DRF's throttling layer.
- The generate endpoint does not currently enforce `request.user.id == student_id`; it relies on `IsStudent` plus the application-level lookup. A defensive layer could overwrite `student_id = request.user.id` server-side to prevent a student from accidentally requesting another student's certificate, even though the row would still be issued only to the configured student.
- Issuing certificates anchored to passing thresholds aligns with formative-summative pedagogy patterns where AI-curated remediation (CU-09) and human-issued credentials remain distinct artifacts; the certificate does not surface AI-generated commentary, only the immutable issuance record (Okonkwo et al., 2026).
- Modality data is not part of the certificate payload — the persisted `Certificate` row does not record VARK; it is purely a course-completion proof. Modality only affects the upstream remediation pathway (Alharbi et al., 2025).

## Request / Response

`POST /api/v1/certificates/generate/` — HTTP 201

Request:

```json
{
  "student_id": 2,
  "course_id": 12
}
```

Response (newly issued or pre-existing — idempotent):

```json
{
  "certificate_hash": "4ef1fcd7c1cbfa4470d1906a5ec2fce35299f4e9d6ae3722742cc8a27bc653f6",
  "issued_at": "2026-04-25T17:35:10.251114+00:00",
  "course_id": 12,
  "student_id": 2
}
```

Ineligibility (HTTP 403):

```json
{ "error": "ineligible", "detail": "No passing evaluation or quiz attempt found (minimum score: 60.00)." }
```

`GET /api/v1/certificates/verify/4ef1fcd7c1cbfa4470d1906a5ec2fce35299f4e9d6ae3722742cc8a27bc653f6/` — HTTP 200

Response:

```json
{
  "is_valid": true,
  "hash": "4ef1fcd7c1cbfa4470d1906a5ec2fce35299f4e9d6ae3722742cc8a27bc653f6",
  "issued_at": "2026-04-25T17:35:10.251114+00:00",
  "student_name": "Alice Doe",
  "course_name": "Advanced Programming"
}
```

Hash not found (HTTP 404):

```json
{ "is_valid": false, "detail": "Certificate not found." }
```
