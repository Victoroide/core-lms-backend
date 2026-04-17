# 06 -- API Reference

> PUDS -- AxiomLMS REST API Reference
> Version 1.0 | 2026-04-16

---

## General Conventions

- **Base URL:** `/api/v1/`
- **Authentication:** JWT Bearer token in the `Authorization` header (`Authorization: Bearer <access_token>`), except where noted as `AllowAny`.
- **Content-Type:** `application/json` for all non-file endpoints. `multipart/form-data` for file uploads.
- **Pagination:** All list endpoints use `PageNumberPagination` with `PAGE_SIZE=20`.
- **List response envelope:**

```json
{
  "count": 142,
  "next": "http://host/api/v1/resource/?page=2",
  "previous": null,
  "results": [...]
}
```

- **Soft-deleted records** are excluded from list and detail responses by default. Pass `?is_deleted=true` where the filter is supported to include them.
- **Error responses** follow DRF conventions: `{"detail": "Error message"}` for single errors, `{"field_name": ["Error message"]}` for validation errors.

---

## 1. Authentication

### POST /api/v1/auth/token/

Obtain a JWT access/refresh token pair.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | AllowAny                 |
| Content-Type  | application/json         |

**Request Body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Success Response (200):**

```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Token pair returned                  |
| 401  | Invalid credentials                  |

---

### POST /api/v1/auth/token/refresh/

Refresh an expired access token using a valid refresh token.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | AllowAny                 |
| Content-Type  | application/json         |

**Request Body:**

```json
{
  "refresh": "eyJ..."
}
```

**Success Response (200):**

```json
{
  "access": "eyJ..."
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | New access token returned            |
| 401  | Refresh token invalid or expired     |

---

### Token Lifetime and Rotation

- Access token lifetime: **30 minutes**
- Refresh token lifetime: **7 days**
- Refresh tokens rotate on use. The previous refresh token is **blacklisted immediately** after rotation. The frontend must persist the new refresh token returned in each `/token/refresh/` response.
- After 7 days of inactivity, the user must re-authenticate via `/token/`.
- The `/token/` endpoint is rate-limited to **10 POST requests per minute per IP**. Exceeding the limit returns HTTP 429.

---

## 2. Academic Ontology

All academic ontology endpoints follow a consistent CRUD pattern. Read operations (GET) require `IsAuthenticated`. Write operations (POST, PUT, PATCH, DELETE) require `IsTutor`.

### /api/v1/careers/

Manage academic careers (degree programs).

| Method | Path                    | Permission      | Description          |
|--------|-------------------------|-----------------|----------------------|
| GET    | /api/v1/careers/        | IsAuthenticated | List all careers     |
| POST   | /api/v1/careers/        | IsTutor         | Create a career      |
| GET    | /api/v1/careers/{id}/   | IsAuthenticated | Retrieve a career    |
| PUT    | /api/v1/careers/{id}/   | IsTutor         | Full update          |
| PATCH  | /api/v1/careers/{id}/   | IsTutor         | Partial update       |
| DELETE | /api/v1/careers/{id}/   | IsTutor         | Soft delete          |

**Filters:** `is_deleted`

**Request Body (POST/PUT):**

```json
{
  "name": "string (max 200)",
  "code": "string (max 20, unique)",
  "description": "string"
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "name": "Systems Engineering",
  "code": "SIS",
  "description": "...",
  "created_at": "2026-04-16T12:00:00Z",
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Success (GET, PUT, PATCH)            |
| 201  | Created (POST)                       |
| 204  | Deleted (DELETE)                     |
| 400  | Validation error                     |
| 401  | Not authenticated                    |
| 403  | Not a tutor (write operations)       |
| 404  | Career not found                     |

---

### /api/v1/semesters/

Manage semesters within a career.

| Method | Path                      | Permission      | Description           |
|--------|---------------------------|-----------------|---------------------- |
| GET    | /api/v1/semesters/        | IsAuthenticated | List all semesters    |
| POST   | /api/v1/semesters/        | IsTutor         | Create a semester     |
| GET    | /api/v1/semesters/{id}/   | IsAuthenticated | Retrieve a semester   |
| PUT    | /api/v1/semesters/{id}/   | IsTutor         | Full update           |
| PATCH  | /api/v1/semesters/{id}/   | IsTutor         | Partial update        |
| DELETE | /api/v1/semesters/{id}/   | IsTutor         | Soft delete           |

**Filters:** `career`, `is_deleted`

**Request Body (POST/PUT):**

```json
{
  "career": 1,
  "name": "string (max 100)",
  "number": 1,
  "year": 2026,
  "period": "string (max 6)"
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "career": 1,
  "name": "First Semester",
  "number": 1,
  "year": 2026,
  "period": "I-2026",
  "created_at": "2026-04-16T12:00:00Z",
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:** Same as careers.

---

### /api/v1/courses/

Manage courses within a semester.

| Method | Path                    | Permission      | Description         |
|--------|-------------------------|-----------------|---------------------|
| GET    | /api/v1/courses/        | IsAuthenticated | List all courses    |
| POST   | /api/v1/courses/        | IsTutor         | Create a course     |
| GET    | /api/v1/courses/{id}/   | IsAuthenticated | Retrieve a course   |
| PUT    | /api/v1/courses/{id}/   | IsTutor         | Full update         |
| PATCH  | /api/v1/courses/{id}/   | IsTutor         | Partial update      |
| DELETE | /api/v1/courses/{id}/   | IsTutor         | Soft delete         |

**Filters:** `semester`, `semester__career`, `is_deleted`

**Request Body (POST/PUT):**

```json
{
  "semester": 1,
  "name": "string (max 200)",
  "code": "string (max 20, unique)",
  "description": "string"
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "semester": 1,
  "name": "Introduction to Programming",
  "code": "CS101",
  "description": "...",
  "created_at": "2026-04-16T12:00:00Z",
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:** Same as careers.

---

### /api/v1/modules/

Manage modules within a course.

| Method | Path                    | Permission      | Description         |
|--------|-------------------------|-----------------|---------------------|
| GET    | /api/v1/modules/        | IsAuthenticated | List all modules    |
| POST   | /api/v1/modules/        | IsTutor         | Create a module     |
| GET    | /api/v1/modules/{id}/   | IsAuthenticated | Retrieve a module   |
| PUT    | /api/v1/modules/{id}/   | IsTutor         | Full update         |
| PATCH  | /api/v1/modules/{id}/   | IsTutor         | Partial update      |
| DELETE | /api/v1/modules/{id}/   | IsTutor         | Soft delete         |

**Filters:** `course`, `is_deleted`

**Request Body (POST/PUT):**

```json
{
  "course": 1,
  "title": "string (max 200)",
  "description": "string",
  "order": 1
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "course": 1,
  "title": "Variables and Data Types",
  "description": "...",
  "order": 1,
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:** Same as careers.

---

### /api/v1/lessons/

Manage lessons within a module.

| Method | Path                    | Permission      | Description         |
|--------|-------------------------|-----------------|---------------------|
| GET    | /api/v1/lessons/        | IsAuthenticated | List all lessons    |
| POST   | /api/v1/lessons/        | IsTutor         | Create a lesson     |
| GET    | /api/v1/lessons/{id}/   | IsAuthenticated | Retrieve a lesson   |
| PUT    | /api/v1/lessons/{id}/   | IsTutor         | Full update         |
| PATCH  | /api/v1/lessons/{id}/   | IsTutor         | Partial update      |
| DELETE | /api/v1/lessons/{id}/   | IsTutor         | Soft delete         |

**Filters:** `module`, `is_deleted`

**Request Body (POST/PUT):**

```json
{
  "module": 1,
  "title": "string (max 200)",
  "content": "string",
  "order": 1
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "module": 1,
  "title": "Integer Types",
  "content": "...",
  "order": 1,
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:** Same as careers.

---

## 3. Resources

### /api/v1/resources/

Manage lesson-attached resources (files stored on S3).

| Method | Path                      | Permission      | Description          |
|--------|---------------------------|-----------------|----------------------|
| GET    | /api/v1/resources/        | IsAuthenticated | List all resources   |
| POST   | /api/v1/resources/        | IsTutor         | Upload a resource    |
| GET    | /api/v1/resources/{id}/   | IsAuthenticated | Retrieve a resource  |
| PUT    | /api/v1/resources/{id}/   | IsTutor         | Full update          |
| PATCH  | /api/v1/resources/{id}/   | IsTutor         | Partial update       |
| DELETE | /api/v1/resources/{id}/   | IsTutor         | Soft delete          |

**Filters:** `lesson`, `resource_type`, `is_deleted`

**Request Body (POST -- multipart/form-data):**

| Field          | Type   | Required | Description                         |
|----------------|--------|----------|-------------------------------------|
| lesson         | int    | yes      | Lesson ID                           |
| file           | file   | yes      | The file to upload                  |
| resource_type  | string | yes      | One of: pdf, image, video, link     |
| title          | string | yes      | Display title (max 255)             |

**Response (200/201):**

```json
{
  "id": 1,
  "lesson": 1,
  "uploaded_by": 3,
  "file": "https://s3.amazonaws.com/bucket/resources/...",
  "resource_type": "pdf",
  "title": "Chapter 1 Slides",
  "created_at": "2026-04-16T12:00:00Z",
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Success (GET, PUT, PATCH)            |
| 201  | Created (POST)                       |
| 204  | Deleted (DELETE)                     |
| 400  | Validation error or file too large   |
| 401  | Not authenticated                    |
| 403  | Not a tutor (write operations)       |
| 404  | Resource not found                   |

---

## 4. Assignments

### /api/v1/assignments/

Manage lesson assignments.

| Method | Path                        | Permission      | Description            |
|--------|-----------------------------|-----------------|------------------------|
| GET    | /api/v1/assignments/        | IsAuthenticated | List all assignments   |
| POST   | /api/v1/assignments/        | IsTutor         | Create an assignment   |
| GET    | /api/v1/assignments/{id}/   | IsAuthenticated | Retrieve an assignment |
| PUT    | /api/v1/assignments/{id}/   | IsTutor         | Full update            |
| PATCH  | /api/v1/assignments/{id}/   | IsTutor         | Partial update         |
| DELETE | /api/v1/assignments/{id}/   | IsTutor         | Soft delete            |

**Filters:** `lesson`, `created_by`, `is_deleted`

**Request Body (POST/PUT):**

```json
{
  "lesson": 1,
  "title": "string (max 255)",
  "description": "string",
  "due_date": "2026-05-01T23:59:00Z",
  "max_score": 100.00
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "lesson": 1,
  "created_by": 3,
  "title": "Lab Exercise 1",
  "description": "...",
  "due_date": "2026-05-01T23:59:00Z",
  "max_score": 100.00,
  "created_at": "2026-04-16T12:00:00Z",
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:** Same as resources.

---

## 5. Submissions

### /api/v1/submissions/

Manage student assignment submissions with row-level isolation (students see only their own submissions).

| Method | Path                              | Permission  | Description                    |
|--------|-----------------------------------|-------------|--------------------------------|
| GET    | /api/v1/submissions/              | IsAuthenticated | List submissions           |
| POST   | /api/v1/submissions/              | IsStudent   | Submit an assignment           |
| GET    | /api/v1/submissions/{id}/         | IsAuthenticated | Retrieve a submission      |
| PATCH  | /api/v1/submissions/{id}/grade/   | IsTutor     | Grade a submission             |
| DELETE | /api/v1/submissions/{id}/         | IsTutor     | Soft delete                    |

**Filters:** `assignment`, `is_deleted`

**Request Body (POST -- multipart/form-data):**

| Field       | Type   | Required | Description                   |
|-------------|--------|----------|-------------------------------|
| assignment  | int    | yes      | Assignment ID                 |
| file        | file   | yes      | The submission file            |

**Request Body (PATCH /grade/):**

```json
{
  "grade": 85.50
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "assignment": 1,
  "student": 5,
  "file": "https://s3.amazonaws.com/bucket/submissions/...",
  "submitted_at": "2026-04-16T14:30:00Z",
  "grade": null,
  "graded_at": null,
  "is_deleted": false,
  "deleted_at": null
}
```

**Status Codes:**

| Code | Meaning                                        |
|------|------------------------------------------------|
| 200  | Success (GET, PATCH)                           |
| 201  | Created (POST)                                 |
| 204  | Deleted (DELETE)                               |
| 400  | Validation error, duplicate submission         |
| 401  | Not authenticated                              |
| 403  | Permission denied                              |
| 404  | Submission not found                           |

---

## 6. Quizzes

### /api/v1/quizzes/

Read-only access to quizzes with nested questions and answer choices.

| Method | Path                    | Permission | Description               |
|--------|-------------------------|------------|---------------------------|
| GET    | /api/v1/quizzes/        | AllowAny   | List all active quizzes   |
| GET    | /api/v1/quizzes/{id}/   | AllowAny   | Retrieve quiz with questions and choices |

**Filters:** None (read-only, active quizzes only).

**Response (200):**

```json
{
  "id": 1,
  "course": 1,
  "title": "Midterm Exam",
  "description": "...",
  "time_limit_minutes": 30,
  "is_active": true,
  "created_at": "2026-04-16T12:00:00Z",
  "questions": [
    {
      "id": 1,
      "text": "What is a variable?",
      "concept_id": "variables_basics",
      "order": 1,
      "answer_choices": [
        {
          "id": 1,
          "text": "A named storage location in memory",
          "is_correct": true
        },
        {
          "id": 2,
          "text": "A type of loop",
          "is_correct": false
        }
      ]
    }
  ]
}
```

Note: The `is_correct` field is intentionally excluded from the `AnswerChoice` serializer. Student-facing quiz detail responses never expose correct answers.

**Status Codes:**

| Code | Meaning              |
|------|----------------------|
| 200  | Success              |
| 404  | Quiz not found       |

---

## 7. Attempts

### Attempts

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | /api/v1/attempts/ | IsStudent | Submit a completed quiz; returns score and adaptive plan |
| GET | /api/v1/attempts/ | IsStudent | List the authenticated student's quiz attempts (paginated, row-level scoped) |
| GET | /api/v1/attempts/{id}/ | IsStudent | Retrieve a single attempt owned by the authenticated student |

**Note:** Multiple attempts per (student, quiz) are allowed. A student may retake a quiz to improve their score and trigger an updated adaptive study plan.

**Row-level scoping:** Students see only their own attempts. Attempting to retrieve another student's attempt returns 404.

### POST /api/v1/attempts/

Submit a quiz attempt with answers. Triggers automated scoring and adaptive plan generation via AxiomEngine.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | IsStudent                |
| Content-Type  | application/json         |

**Request Body:**

```json
{
  "quiz_id": 1,
  "student_id": 5,
  "answers": [
    {
      "question_id": 1,
      "selected_choice_id": 3
    },
    {
      "question_id": 2,
      "selected_choice_id": 7
    }
  ]
}
```

**Success Response (201):**

```json
{
  "attempt_id": 42,
  "quiz_id": 1,
  "student_id": 5,
  "final_score": 75.00,
  "is_submitted": true,
  "start_time": "2026-04-16T14:00:00Z",
  "end_time": "2026-04-16T14:25:00Z",
  "failed_topics": [
    {
      "concept_id": "recursion_basics",
      "score": 0.00,
      "max_score": 25.00
    }
  ],
  "adaptive_plan": {
    "plan": [
      {
        "concept_id": "recursion_basics",
        "recommended_resources": ["..."],
        "estimated_time_minutes": 45,
        "difficulty": "intermediate"
      }
    ],
    "fallback": false
  }
}
```

**Status Codes:**

| Code | Meaning                                        |
|------|------------------------------------------------|
| 201  | Attempt created, scored, and plan generated    |
| 400  | Validation error (missing answers, invalid IDs)|
| 401  | Not authenticated                              |
| 403  | Not a student                                  |

Note: If the AxiomEngine is unreachable, the response still returns 201 with `"adaptive_plan": {"plan": [], "fallback": true}`.

---

## 8. Proctoring

### POST /api/v1/proctoring/logs/

Bulk-create proctoring event logs for a quiz attempt. Called by the Angular frontend's proctoring module during an active quiz session.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | IsStudent                |
| Content-Type  | application/json         |

**Request Body:**

```json
{
  "events": [
    {
      "attempt": 42,
      "event_type": "tab_switch",
      "timestamp": "2026-04-16T14:10:23Z",
      "severity_score": 0.80
    },
    {
      "attempt": 42,
      "event_type": "face_absence",
      "timestamp": "2026-04-16T14:12:05Z",
      "severity_score": 0.95
    }
  ]
}
```

**Success Response (201):**

```json
{
  "created": 2
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 201  | Logs created                         |
| 400  | Validation error                     |
| 401  | Not authenticated                    |
| 403  | Not a student                        |

**Supported event_type values:** `tab_switch`, `face_absence`, `copy_paste`, `window_resize`, `right_click`, `devtools_open`

---

## 9. Analytics

### GET /api/v1/analytics/course/{id}/dashboard/

Retrieve an analytics dashboard for a specific course. Aggregates proctoring data, VARK distribution, and commonly failed concepts.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | IsTutor                  |
| Content-Type  | application/json         |

**Path Parameters:**

| Parameter | Type | Description       |
|-----------|------|-------------------|
| id        | int  | Course ID         |

**Success Response (200):**

```json
{
  "proctoring_alerts": [
    {
      "student_id": 5,
      "student_name": "Jane Doe",
      "attempt_id": 42,
      "total_events": 7,
      "avg_severity": 0.72
    }
  ],
  "vark_distribution": {
    "visual": 12,
    "auditory": 8,
    "reading": 15,
    "kinesthetic": 5
  },
  "top_failed_concepts": [
    {
      "concept_id": "recursion_basics",
      "failure_count": 23,
      "avg_score_ratio": 0.35
    },
    {
      "concept_id": "pointer_arithmetic",
      "failure_count": 18,
      "avg_score_ratio": 0.42
    }
  ]
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Dashboard data returned              |
| 401  | Not authenticated                    |
| 403  | Not a tutor                          |
| 404  | Course not found                     |

---

## 10. Certificates

### POST /api/v1/certificates/generate/

Generate a completion certificate for a student in a course. Creates a SHA-256 hash for tamper detection. Fails if a certificate already exists for the student-course pair.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | IsStudent                |
| Content-Type  | application/json         |

**Request Body:**

```json
{
  "student_id": 5,
  "course_id": 1
}
```

**Success Response (201):**

```json
{
  "certificate_hash": "a3f2b8c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
  "issued_at": "2026-04-16T15:00:00Z",
  "course_id": 1,
  "student_id": 5
}
```

**Status Codes:**

| Code | Meaning                                          |
|------|--------------------------------------------------|
| 201  | Certificate generated                            |
| 400  | Certificate already exists for this student-course pair |
| 401  | Not authenticated                                |
| 403  | Not a student                                    |

---

## 11. Users

### POST /api/v1/users/{id}/onboard/

Complete the VARK learning style onboarding for a user. Sets the `vark_dominant` field based on the student's questionnaire responses.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | IsAuthenticated          |
| Content-Type  | application/json         |

**Path Parameters:**

| Parameter | Type | Description    |
|-----------|------|----------------|
| id        | int  | User ID        |

**Request Body:**

```json
{
  "vark_dominant": "visual"
}
```

Valid values for `vark_dominant`: `visual`, `auditory`, `reading`, `kinesthetic`

**Success Response (200):**

```json
{
  "id": 5,
  "username": "jane.doe",
  "role": "student",
  "vark_dominant": "visual"
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Profile updated                      |
| 400  | Invalid VARK value                   |
| 401  | Not authenticated                    |
| 404  | User not found                       |

---

## 12. Evaluations

### /api/v1/evaluations/

Manage student evaluations (scores per course).

| Method | Path                        | Permission      | Description             |
|--------|-----------------------------|-----------------|-------------------------|
| GET    | /api/v1/evaluations/        | IsAuthenticated | List evaluations        |
| POST   | /api/v1/evaluations/        | IsAuthenticated | Create an evaluation    |
| GET    | /api/v1/evaluations/{id}/   | IsAuthenticated | Retrieve an evaluation  |
| PUT    | /api/v1/evaluations/{id}/   | IsAuthenticated | Full update             |
| PATCH  | /api/v1/evaluations/{id}/   | IsAuthenticated | Partial update          |
| DELETE | /api/v1/evaluations/{id}/   | IsAuthenticated | Delete                  |

**Filters:** None specified.

**Request Body (POST/PUT):**

```json
{
  "student": 5,
  "course": 1,
  "score": 85.50,
  "max_score": 100.00
}
```

**Response (200/201):**

```json
{
  "id": 1,
  "student": 5,
  "course": 1,
  "score": 85.50,
  "max_score": 100.00,
  "created_at": "2026-04-16T12:00:00Z"
}
```

**Status Codes:**

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Success (GET, PUT, PATCH)            |
| 201  | Created (POST)                       |
| 204  | Deleted (DELETE)                     |
| 400  | Validation error                     |
| 401  | Not authenticated                    |
| 404  | Evaluation not found                 |

---

## 13. Evaluation Telemetry

### EvaluationTelemetry

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | /api/v1/evaluation-telemetry/ | IsStudent | Create a telemetry record linked to an evaluation |
| GET | /api/v1/evaluation-telemetry/ | IsAuthenticated | List telemetry records (row-scoped for students) |
| GET | /api/v1/evaluation-telemetry/{id}/ | IsAuthenticated | Retrieve a single telemetry record (row-scoped for students) |

**Request Body (POST):**
- `evaluation` (integer, required): Primary key of the Evaluation
- `time_on_task_seconds` (integer, required): Total time on task in seconds
- `clicks` (integer, required): Total click count during the session

**Response fields:** id, evaluation, time_on_task_seconds, clicks

---

## 14. System

### GET /health/

Health check endpoint. Returns a simple status response. No authentication required. This endpoint is outside the `/api/v1/` prefix.

| Attribute     | Value                    |
|---------------|--------------------------|
| Permission    | AllowAny                 |

**Success Response (200):**

```json
{
  "status": "ok"
}
```

**Status Codes:**

| Code | Meaning              |
|------|----------------------|
| 200  | Service is healthy   |

---

## Appendix A: Permission Classes

| Class           | Rule                                                           |
|-----------------|----------------------------------------------------------------|
| AllowAny        | No authentication required.                                    |
| IsAuthenticated | Valid JWT access token required in the Authorization header.   |
| IsStudent       | Authenticated user with `role = "student"`.                    |
| IsTutor         | Authenticated user with `role = "tutor"`.                      |

---

## Appendix B: Common Query Parameters

| Parameter   | Type   | Description                                              |
|-------------|--------|----------------------------------------------------------|
| page        | int    | Page number for pagination (default: 1).                 |
| is_deleted  | bool   | Include soft-deleted records when set to `true`.         |
| ordering    | string | Field name to sort by. Prefix with `-` for descending.  |

---

## Appendix C: HTTP Status Code Summary

| Code | Meaning                                                     |
|------|-------------------------------------------------------------|
| 200  | Request succeeded.                                          |
| 201  | Resource created successfully.                              |
| 204  | Resource deleted successfully (no content returned).        |
| 400  | Bad request -- validation error or malformed input.         |
| 401  | Authentication credentials missing or invalid.              |
| 403  | Authenticated but insufficient permissions.                 |
| 404  | Requested resource does not exist.                          |
| 429  | Rate limit exceeded (AxiomEngine: 50 req/min/IP).          |
| 500  | Internal server error.                                      |

---

## Appendix D: Frontend Integration Guide

This appendix is written for the Angular frontend team integrating with the AxiomLMS backend.

### Base URL and Versioning

All application endpoints are prefixed with `/api/v1/`. Authentication endpoints are at `/api/v1/auth/token/` and `/api/v1/auth/token/refresh/`. The health check is at `/health/` (no versioning). No backwards-incompatible changes will be made within `v1`.

### Authentication Flow

1. On login, `POST /api/v1/auth/token/` with `{"username": "...", "password": "..."}` to obtain `access` and `refresh` tokens.
2. Store both tokens **in memory** (for example, a protected service in Angular). Do not persist them in `localStorage` because of XSS risk.
3. Attach the access token as `Authorization: Bearer <access_token>` on every API request.
4. On a `401` response, `POST /api/v1/auth/token/refresh/` with `{"refresh": "..."}`.
5. Replace the stored access and refresh tokens with the new pair from the response. The previous refresh token is now blacklisted.
6. Retry the original request with the new access token.
7. If `/token/refresh/` returns `401`, the session is expired. Redirect the user to the login screen.

### CORS

The server enforces CORS via `CORS_ALLOWED_ORIGINS`. The frontend origin (e.g. `https://app.example.com`, `http://localhost:4200`) **must** be included in that list on the server. If the origin is missing, browsers will block the request. Coordinate with the backend team to update the origin list on deploy.

### Pagination

Every list endpoint returns a paginated envelope:
```
{
  "count": 123,
  "next": "https://.../api/v1/careers/?page=2",
  "previous": null,
  "results": [...]
}
```

Use the `next` URL for page 2 and onward. Default page size is 20.

### Soft-deleted Records

Soft-deleted records are excluded from all list and detail responses by default. Pass `?is_deleted=false` explicitly only when a filter is required (for example, to hide records that were restored). Do not rely on `?is_deleted=true` returning anything in production.

### File Uploads

File uploads use `multipart/form-data`. The `file` field in responses is a pre-signed S3 URL valid for **1 hour**. Do not cache file URLs beyond 55 minutes -- refresh by GETting the parent resource to get a new signed URL.

### Error Response Format

- Global / view-level errors: `{"detail": "Human readable message."}` with an appropriate HTTP status code.
- Validation errors: `{"field_name": ["error message"], ...}` with HTTP 400.
- Rate-limited token endpoint: `{"detail": "Too many login attempts. Try again later."}` with HTTP 429.

### Rate Limiting

The `/api/v1/auth/token/` endpoint is limited to **10 POST requests per minute per IP**. Implement exponential backoff on 429 responses (e.g. 1s, 2s, 4s, 8s). Do not retry blindly.
