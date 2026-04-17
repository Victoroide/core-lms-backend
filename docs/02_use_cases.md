# 02 -- Use Cases

## UC-01: Student Submits Quiz

| Field          | Value                                                    |
|----------------|----------------------------------------------------------|
| **ID**         | UC-01                                                    |
| **Name**       | Student Submits Quiz                                     |
| **Actor**      | Student                                                  |

### Preconditions

- The Student is authenticated with a valid JWT access token.
- The target Quiz exists and has `is_active = True`.

### Main Flow

1. The Student opens the quiz interface in the Angular frontend, which fetches the Quiz with its Questions and AnswerChoices.
2. The Student selects one AnswerChoice per Question, answering all questions within the time limit.
3. The frontend POSTs the answers to `/api/v1/attempts/`, including the Quiz ID and the list of question-choice pairs.
4. The backend creates a QuizAttempt record and one AttemptAnswer record per question, linking each to the selected AnswerChoice.
5. The ScoringService computes the final score by evaluating each AttemptAnswer against the correct AnswerChoice.
6. The ScoringService creates an Evaluation record (score/max_score) and one FailedTopic record for each concept where the student scored below the threshold.
7. The backend calls the AxiomEngine Go microservice with the list of failed concept IDs to generate an adaptive study plan.
8. The backend stores the adaptive plan on `QuizAttempt.adaptive_plan` and returns the complete result to the frontend, including the score and the adaptive plan.

### Postconditions

- A QuizAttempt record exists with `is_submitted = True` and `final_score` populated.
- `QuizAttempt.adaptive_plan` contains the structured plan from AxiomEngine (or a fallback).
- An Evaluation record links the Student to the Course with the computed score.
- FailedTopic records exist for each concept the student did not pass.

### Exceptions

- **E1 -- AxiomEngine unavailable**: If the Go microservice returns a ConnectionError or Timeout, the backend stores `{"plan": [], "fallback": true}` on `QuizAttempt.adaptive_plan`. The quiz submission still succeeds with the computed score.

---

## UC-02: System Scores Quiz and Triggers Adaptive Plan

| Field          | Value                                                    |
|----------------|----------------------------------------------------------|
| **ID**         | UC-02                                                    |
| **Name**       | System Scores Quiz and Triggers Adaptive Plan            |
| **Actor**      | System                                                   |

### Preconditions

- A QuizAttempt has been submitted with a complete set of AttemptAnswer records (one per Question in the Quiz).

### Main Flow

1. The ScoringService iterates over all AttemptAnswer records and counts correct answers grouped by `concept_id` (from the associated Question).
2. The ScoringService creates an Evaluation record with the aggregate `score` and `max_score` for the attempt.
3. For each concept where the student's score falls below the passing threshold, the ScoringService creates a FailedTopic record referencing the Evaluation, storing the per-concept score and max_score.
4. The ScoringService creates an EvaluationTelemetry record (one-to-one with Evaluation), recording `time_on_task_seconds` and `clicks` captured by the frontend.
5. The AxiomEngineClient POSTs the list of failed concept IDs and the student's VARK profile to the Go microservice endpoint.
6. The Go microservice processes the request: extracts the relevant subgraph from the knowledge graph, performs a topological sort over concept dependencies, fans out content generation requests via BAML to Amazon Nova Micro, merges and deduplicates the generated study resources, and validates the output structure.
7. The Go microservice returns a structured adaptive study plan as a JSON payload.
8. The backend stores the returned plan on `QuizAttempt.adaptive_plan`.

### Postconditions

- An Evaluation record exists linking the student, course, and computed score.
- FailedTopic records exist for every concept the student did not pass.
- An EvaluationTelemetry record exists with behavioral metrics.
- `QuizAttempt.adaptive_plan` is populated with the plan from AxiomEngine or a fallback payload.

### Exceptions

- **E1 -- AxiomEngine timeout or error**: If the Go service does not respond within the configured timeout or returns an error status, the backend catches the exception and stores `{"plan": [], "fallback": true}` on the QuizAttempt. All other records (Evaluation, FailedTopic, EvaluationTelemetry) are still created normally.

---

## UC-03: Tutor Reviews Proctoring Alerts

| Field          | Value                                                    |
|----------------|----------------------------------------------------------|
| **ID**         | UC-03                                                    |
| **Name**       | Tutor Reviews Proctoring Alerts                          |
| **Actor**      | Tutor                                                    |

### Preconditions

- The Tutor is authenticated with a valid JWT access token and has `role = TUTOR`.
- Quiz attempts exist for the target course, and at least some attempts have associated ProctoringLog records.

### Main Flow

1. The Tutor sends a GET request to `/api/v1/analytics/course/{id}/dashboard/`.
2. The backend aggregates data for the specified course and returns a dashboard payload containing: `proctoring_alerts` (grouped counts and details of integrity events), `vark_distribution` (breakdown of student learning modality profiles), and `top_failed_concepts` (ranked list of concepts with the highest failure rates).
3. The Tutor reviews the proctoring alerts section, which surfaces `tab_switched`, `face_not_detected`, and `multiple_faces` events per student attempt, along with severity scores and timestamps.

### Postconditions

- The Tutor has visibility into academic integrity data for the course and can make informed decisions about flagged attempts.

### Exceptions

- None specific. Standard authentication and authorization errors apply (401 if not authenticated, 403 if not a Tutor).

---

## UC-04: Student Downloads Lesson Resource

| Field          | Value                                                    |
|----------------|----------------------------------------------------------|
| **ID**         | UC-04                                                    |
| **Name**       | Student Downloads Lesson Resource                        |
| **Actor**      | Student                                                  |

### Preconditions

- The Student is authenticated with a valid JWT access token.
- The target Resource record exists and is not soft-deleted.

### Main Flow

1. The Student sends a GET request to `/api/v1/resources/{id}/`.
2. The backend retrieves the Resource record and generates an S3 pre-signed URL for the associated file, valid for 1 hour.
3. The response includes the resource metadata (title, resource_type, created_at) along with the pre-signed URL.
4. The Student uses the pre-signed URL to download the file directly from S3.

### Postconditions

- The Student has accessed the file through a temporary, time-limited URL. No persistent public access to the S3 object is granted.

### Exceptions

- **E1 -- S3 unavailable**: If the S3 service is unreachable or the pre-signed URL generation fails, the backend returns a 500 Internal Server Error.
- **E2 -- Resource not found**: If the resource ID does not exist or has been soft-deleted, the backend returns a 404 Not Found.

---

## UC-05: Tutor Grades Submission

| Field          | Value                                                    |
|----------------|----------------------------------------------------------|
| **ID**         | UC-05                                                    |
| **Name**       | Tutor Grades Submission                                  |
| **Actor**      | Tutor                                                    |

### Preconditions

- The Tutor is authenticated with a valid JWT access token and has `role = TUTOR`.
- A Submission record exists for the target assignment, uploaded by a Student.

### Main Flow

1. The Tutor sends a GET request to `/api/v1/submissions/` to retrieve all submissions. The Tutor role grants visibility into all submissions across courses.
2. The Tutor selects a specific submission and sends a PATCH request to `/api/v1/submissions/{id}/grade/` with the payload `{"grade": 85.50}` (example value).
3. The backend sets the `grade` field on the Submission record and populates `graded_at` with the current timestamp.

### Postconditions

- The Submission record has a non-null `grade` and `graded_at` timestamp.
- The Student can see the grade when querying their submissions.

### Exceptions

- **E1 -- Student attempts to grade (403)**: If a user with `role = STUDENT` sends a PATCH to the grade endpoint, the backend returns 403 Forbidden.
- **E2 -- Submission not found**: If the submission ID does not exist or has been soft-deleted, the backend returns 404 Not Found.

---

## UC-06: System Issues Certificate

| Field          | Value                                                    |
|----------------|----------------------------------------------------------|
| **ID**         | UC-06                                                    |
| **Name**       | System Issues Certificate                                |
| **Actor**      | Student (initiates), System (processes)                  |

### Preconditions

- The Student is authenticated with a valid JWT access token.
- The Student has a passing Evaluation for the target Course (score >= 60.00 out of max_score) or a passing QuizAttempt.

### Main Flow

1. The Student (or a system trigger) sends a POST request to `/api/v1/certificates/generate/` with `student_id` and `course_id` in the payload.
2. The CertificateGenerator service verifies that the student meets the eligibility criteria by checking for a passing Evaluation or QuizAttempt linked to the specified course.
3. The service computes a SHA-256 hash from the composite key (student_id, course_id, issued_at) to produce a unique, verifiable certificate identifier.
4. The service creates a Certificate record with the computed `certificate_hash` and the `issued_at` timestamp.
5. The response returns the `certificate_hash` and `issued_at` to the caller.

### Postconditions

- A Certificate record exists in the database with a unique `certificate_hash`.
- The `unique_together` constraint on (student, course) ensures one certificate per student per course.

### Exceptions

- **E1 -- Student not eligible (403)**: If no passing Evaluation or QuizAttempt exists for the given student-course pair, the backend returns 403 Forbidden.
- **E2 -- Certificate already exists (idempotent)**: If a Certificate record already exists for the student-course pair, the backend returns the existing certificate rather than creating a duplicate. The operation is idempotent.
