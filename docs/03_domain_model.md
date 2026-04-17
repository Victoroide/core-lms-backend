# 03 -- Domain Model

## 1. Class Diagram

```
+------------------+          +------------------+          +------------------+
|     LMSUser      |          |      Career      |          |    Semester      |
|------------------|          |------------------|          |------------------|
| (AbstractUser)   |          | name             |          | career  -> Career|
| role             |          | code  [unique]   |          | name             |
| vark_dominant    |          | description      |          | number           |
+------------------+          | created_at       |          | year             |
        |                     | [SoftDelete]     |          | period           |
        |                     +------------------+          | created_at       |
        |                            |  1                   | [SoftDelete]     |
        |                            |                      +------------------+
        |                            | has many                    |  1
        |                            v                             |
        |                     +------------------+                 | has many
        |                     |    Semester      |-----------------+
        |                     +------------------+
        |                            |  1
        |                            | has many
        |                            v
        |                     +------------------+
        |                     |     Course       |
        |                     |------------------|
        |                     | semester -> Semester (nullable)
        |                     | name             |
        |                     | code  [unique]   |
        |                     | description      |
        |                     | created_at       |
        |                     | [SoftDelete]     |
        |                     +------------------+
        |                       |  1          |  1
        |          +------------+             +-------------+
        |          | has many                   has many    |
        |          v                                        v
        |   +------------------+                  +------------------+
        |   |     Module       |                  |       Quiz       |
        |   |------------------|                  |------------------|
        |   | course -> Course |                  | course -> Course |
        |   | title            |                  | title            |
        |   | description      |                  | description      |
        |   | order            |                  | time_limit_min   |
        |   | [SoftDelete]     |                  | is_active        |
        |   +------------------+                  | created_at       |
        |          |  1                           +------------------+
        |          | has many                            |  1
        |          v                                     | has many
        |   +------------------+                         v
        |   |     Lesson       |                  +------------------+
        |   |------------------|                  |    Question      |
        |   | module -> Module |                  |------------------|
        |   | title            |                  | quiz -> Quiz     |
        |   | content          |                  | text             |
        |   | order            |                  | concept_id       |
        |   | [SoftDelete]     |                  | order            |
        |   +------------------+                  +------------------+
        |     |  1        |  1                           |  1
        |     |           |                              | has many
        |     |           | has many                     v
        |     |           v                       +------------------+
        |     |    +------------------+           |  AnswerChoice    |
        |     |    |   Assignment     |           |------------------|
        |     |    |  (curriculum)    |           | question -> Q    |
        |     |    |------------------|           | text             |
        |     |    | lesson -> Lesson |           | is_correct       |
        |     |    | created_by ->User|           +------------------+
        |     |    | title            |                  |
        |     |    | description      |                  | selected in
        |     |    | due_date         |                  v
        |     |    | max_score        |           +------------------+
        |     |    | [SoftDelete]     |           | AttemptAnswer    |
        |     |    +------------------+           |------------------|
        |     |           |  1                    | attempt -> QA    |
        |     |           | has many              | question -> Q    |
        |     |           v                       | selected_choice  |
        |     |    +------------------+           |   -> AC          |
        |     |    |   Submission     |           +------------------+
        |     |    |  (curriculum)    |                  ^
        |     |    |------------------|                  | has many
        |     |    | assignment -> A  |                  |
        |     |    | student -> User  |           +------------------+
        |     |    | file             |           |   QuizAttempt    |
        |     |    | submitted_at     |           |------------------|
        |     |    | grade            |           | student -> User  |
        |     |    | graded_at        |           | quiz -> Quiz     |
        |     |    | [SoftDelete]     |           | start_time       |
        |     |    +------------------+           | end_time         |
        |     |                                   | final_score      |
        |     | has many                          | is_submitted     |
        |     v                                   | adaptive_plan    |
        |   +------------------+                  |   (JSONField)    |
        |   |    Resource      |                  +------------------+
        |   |------------------|                         |  1
        |   | lesson -> Lesson |                         | has many
        |   | uploaded_by->User|                         v
        |   | file             |                  +------------------+
        |   | resource_type    |                  | ProctoringLog    |
        |   | title            |                  |------------------|
        |   | created_at       |                  | attempt -> QA    |
        |   | [SoftDelete]     |                  | event_type       |
        |   +------------------+                  | timestamp        |
        |                                         | severity_score   |
        |                                         +------------------+
        |
        |         +------------------+         +---------------------+
        +-------->|   Evaluation     |-------->| EvaluationTelemetry |
        |         |------------------|  1 : 1  |---------------------|
        |         | student -> User  |         | evaluation -> Eval  |
        |         | course -> Course |         | time_on_task_seconds|
        |         | score            |         | clicks              |
        |         | max_score        |         +---------------------+
        |         | created_at       |
        |         +------------------+
        |                |  1
        |                | has many
        |                v
        |         +------------------+
        |         |   FailedTopic    |
        |         |------------------|
        |         | evaluation ->Eval|
        |         | concept_id       |
        |         | score            |
        |         | max_score        |
        |         +------------------+
        |
        |         +------------------+
        +-------->|   Certificate    |
                  |------------------|
                  | student -> User  |
                  | course -> Course |
                  | issued_at        |
                  | certificate_hash |
                  |   [unique]       |
                  +------------------+
```

### Relationship Summary

```
Career          1 ----* Semester
Semester        1 ----* Course          (Course.semester is nullable)
Course          1 ----* Module
Course          1 ----* Quiz
Course          1 ----* Evaluation
Course          1 ----* Certificate
Module          1 ----* Lesson
Lesson          1 ----* Resource
Lesson          1 ----* Assignment      (curriculum app)
Assignment      1 ----* Submission      (curriculum app)
Quiz            1 ----* Question
Question        1 ----* AnswerChoice
Quiz            1 ----* QuizAttempt     (via attempts)
QuizAttempt     1 ----* AttemptAnswer
QuizAttempt     1 ----* ProctoringLog
AttemptAnswer   * ----1 Question
AttemptAnswer   * ----1 AnswerChoice
Evaluation      1 ----1 EvaluationTelemetry
Evaluation      1 ----* FailedTopic
LMSUser         1 ----* QuizAttempt
LMSUser         1 ----* Evaluation
LMSUser         1 ----* Certificate
LMSUser         1 ----* Submission      (as student)
LMSUser         1 ----* Assignment      (as created_by)
LMSUser         1 ----* Resource        (as uploaded_by)
```

## 2. Model Descriptions

### LMSUser

Extends Django's AbstractUser to add two EdTech-specific fields: `role` (STUDENT or TUTOR) which drives RBAC permission checks across the API, and `vark_dominant` (visual, aural, read_write, or kinesthetic) which records the student's dominant learning modality. The VARK profile is transmitted to AxiomEngine when generating adaptive plans so that study resources can be tailored to the student's preferred learning style. Database table: `lms_user`.

### Career

The top-level node in the academic ontology hierarchy. Represents a university degree program (e.g., Systems Engineering, Medicine). Each Career has a unique `code` used as a short identifier and a `name` for display. Uses the SoftDelete pattern, meaning deletion sets `is_deleted = True` rather than removing the row. Careers contain Semesters. Database table: `career`.

### Semester

An academic period within a Career. Groups courses offered during a specific `year` and `period` (First, Second, or Summer). The `number` field defines the ordinal position within the career curriculum. A unique constraint on (career, number, year) prevents duplicate semester definitions. Uses the SoftDelete pattern. Database table: `semester`.

### Course

An academic course optionally linked to a Semester (the FK is nullable, allowing standalone courses). Each Course has a unique `code` and serves as the anchor point for Modules (content structure), Quizzes (assessments), Evaluations (scoring records), and Certificates. Uses the SoftDelete pattern. Database table: `course`.

### Module

A thematic section within a Course that groups related Lessons. The `order` field controls display sequence within the parent Course. Each Module contains one or more Lessons. Uses the SoftDelete pattern. Database table: `module`.

### Lesson

The atomic pedagogical unit within a Module. Contains a `title` and `content` field (rich text or markdown) for the lesson body, plus an `order` field for sequencing within the Module. Lessons are the attachment point for both Resources (file-based learning materials) and Assignments (deliverable-based assessments). Uses the SoftDelete pattern. Database table: `lesson`.

### Resource

A file-based learning resource attached to a Lesson and uploaded by a user (typically a Tutor). The `file` field stores the upload in S3 via a custom upload path. The `resource_type` field categorizes the file as PDF, VIDEO, DOCUMENT, IMAGE, or OTHER. Access is controlled through S3 pre-signed URLs. Uses the SoftDelete pattern. Database table: `resource`.

### Evaluation

Records the outcome of a scored assessment for a specific student-course pair. Stores `score` and `max_score` as decimal fields (max_digits=6, decimal_places=2). Each Evaluation can have one EvaluationTelemetry record and multiple FailedTopic records. Created automatically by the ScoringService after a quiz is submitted and scored. Database table: `evaluation`.

### FailedTopic

Represents a single concept that a student failed within an Evaluation. The `concept_id` field must match a node name in the AxiomEngine knowledge graph, establishing the bridge between assessment results and adaptive plan generation. Stores per-concept `score` and `max_score` to quantify the degree of failure. Database table: `failed_topic`.

### EvaluationTelemetry

Client-side behavioral telemetry captured during an evaluation session, linked one-to-one with an Evaluation. Records `time_on_task_seconds` (total time spent) and `clicks` (interaction count). This data supports learning analytics and can inform future adaptive plan calibration. Database table: `evaluation_telemetry`.

### Certificate

Issued when a student satisfactorily completes a course. The `certificate_hash` is a SHA-256 hex digest computed by the CertificateGenerator service from the composite key (student_id, course_id, issued_at), providing a unique, verifiable credential identifier. The `unique_together` constraint on (student, course) ensures at most one certificate per student per course, making the issuance operation idempotent. Database table: `certificate`.

### Quiz

A timed assessment instrument linked to a specific Course. Key fields include `title`, `time_limit_minutes` (default 30), and `is_active` (controls whether students can take the quiz). Each Quiz contains multiple Questions. Database table: `quiz`.

### Question

A single multiple-choice question within a Quiz. The `concept_id` field maps directly to a node name in the AxiomEngine knowledge graph, enabling automatic identification of failed concepts after scoring. The `order` field controls display sequence. Each Question has multiple AnswerChoices. Database table: `question`.

### AnswerChoice

One of several possible answers for a Question. The `is_correct` boolean flag identifies the correct choice. Exactly one AnswerChoice per Question should have `is_correct = True`. The `text` field holds the answer content (up to 500 characters). Database table: `answer_choice`.

### QuizAttempt

Records a student's attempt at a specific Quiz. Tracks `start_time`, `end_time`, `final_score`, and `is_submitted` status. The `adaptive_plan` JSONField stores the structured study plan returned by AxiomEngine (or a fallback payload if the service was unavailable). Each attempt has multiple AttemptAnswers and may have ProctoringLog entries. Database table: `quiz_attempt`.

### AttemptAnswer

Links a student's selected AnswerChoice to a specific Question within a QuizAttempt. The `unique_together` constraint on (attempt, question) ensures a student can only answer each question once per attempt. Used by the ScoringService to compute results by comparing selected choices against correct answers. Database table: `attempt_answer`.

### ProctoringLog

An anti-cheat telemetry event captured by the frontend proctoring system (face-api.js or tab-visibility API) during a quiz attempt. The `event_type` field is one of: `tab_switched`, `face_not_detected`, or `multiple_faces`. Each event carries a `timestamp` and a `severity_score` (decimal, default 1.00). Logs are stored per-attempt and surfaced on tutor analytics dashboards for post-hoc integrity analysis. Database table: `proctoring_log`.

### Assignment (curriculum app)

A tutor-created deliverable attached to a specific Lesson. Defines a `title`, `description` with instructions, an optional `due_date` deadline, and a `max_score` (default 100). The `created_by` FK links to the Tutor who created the assignment. Students respond by uploading Submissions. Uses the SoftDelete pattern. Database table: `assignment`.

### Submission (curriculum app)

A student-uploaded file submission for a specific Assignment. The `file` field stores the upload in S3 via a custom upload path. Initially, `grade` and `graded_at` are null; a Tutor populates them through the grading endpoint. The `unique_together` constraint on (assignment, student) ensures one submission per student per assignment. Uses the SoftDelete pattern. Database table: `submission`.
