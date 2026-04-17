# 01 -- System Vision

## 1. System Purpose

AxiomLMS is an AI-driven Learning Management System built on Django 5.1.7 and Django REST Framework. Its primary differentiator is the integration with AxiomEngine, an external Go microservice that generates adaptive study plans for students based on their quiz performance. AxiomEngine operates on a GraphRAG architecture over a concept topology (knowledge graph), using Amazon Nova Micro via BAML for content generation. The Django backend manages the full academic lifecycle -- course content, assessments, proctoring, grading, and certification -- while delegating intelligent plan generation to the Go service. An Angular frontend consumes the REST API, and production infrastructure relies on PostgreSQL (NeonDB), AWS S3 for file storage, and JWT-based authentication.

## 2. Actors

### 2.1 Student

The Student is the primary consumer of the platform. Students enroll in courses structured under the academic ontology, take timed quizzes, view lesson resources, submit file-based assignments, and receive AI-generated adaptive study plans when quiz performance reveals knowledge gaps. Students can also request certificates upon satisfactory course completion.

### 2.2 Tutor

The Tutor is the content creator and academic authority. Tutors create courses, modules, lessons, and quizzes. They upload resources (PDFs, videos, documents) to lessons, define assignments with due dates, grade student submissions, and review proctoring alerts to monitor academic integrity. Tutors have read access to analytics dashboards that surface VARK distribution, failed-concept rankings, and proctoring event summaries.

### 2.3 System / AxiomEngine

The System actor encompasses both the Django backend and the AxiomEngine Go microservice. The backend automatically scores quizzes upon submission, creates evaluation records, identifies failed concepts, and records behavioral telemetry. It then delegates to AxiomEngine, which extracts a subgraph from the knowledge graph based on the failed concepts, performs a topological sort, fans out content generation requests via BAML to Amazon Nova Micro, merges and deduplicates results, validates the output, and returns a structured adaptive study plan. The backend also handles certificate issuance by computing SHA-256 verification hashes.

## 3. Scope

### 3.1 Included

- **Academic ontology**: A hierarchical content structure following the chain Career -> Semester -> Course -> Module -> Lesson. Each level supports soft deletion and ordered traversal.
- **Quiz assessment with adaptive planning**: Timed quizzes composed of multiple-choice questions, each tagged with a concept_id that maps to a node in the AxiomEngine knowledge graph. Upon submission, the system scores the attempt, identifies failed concepts, and requests an adaptive plan from AxiomEngine.
- **File-based assignments and submissions**: Tutors create assignments attached to lessons. Students upload file submissions to S3. Tutors grade submissions through the API.
- **Proctoring**: Client-side proctoring events (tab switches, face not detected, multiple faces detected) are recorded per quiz attempt and surfaced on tutor analytics dashboards.
- **Certificates**: System-issued certificates with SHA-256 verification hashes, generated upon confirmed course completion with a passing evaluation.
- **Resource management**: File-based learning resources (PDF, video, document, image) stored in S3 with pre-signed URL access.

### 3.2 Not Included

- Real-time chat or messaging between students and tutors.
- Video conferencing or live classroom sessions.
- Payment processing, billing, or subscription management.

## 4. Quality Attributes

### 4.1 Security

Authentication is handled via SimpleJWT with a 2-hour access token lifetime and a 7-day refresh token lifetime. Role-Based Access Control is enforced through custom DRF permission classes (IsStudent, IsTutor) that inspect the LMSUser.role field on every request. File storage on AWS S3 uses private ACL, and all file access is mediated through pre-signed URLs with a 1-hour expiration window, ensuring that no S3 object is publicly accessible.

### 4.2 Availability

The system implements a graceful degradation pattern for AxiomEngine dependency. When the Go microservice is unreachable (ConnectionError) or exceeds its response deadline (Timeout), the backend catches the exception and stores a fallback response on the QuizAttempt record: `{"plan": [], "fallback": true}`. This ensures that quiz submission never fails due to AxiomEngine unavailability; the student receives their score immediately and the adaptive plan is marked as degraded.

### 4.3 Maintainability

The codebase follows a split-directory topology within each Django app, organizing code into `models/`, `serializers/`, `viewsets/`, and `services/` directories. This structure keeps each concern isolated and allows parallel development across features. A soft-delete pattern (via SoftDeleteMixin, SoftDeleteManager, and AllObjectsManager) is applied to 8 domain models: Career, Semester, Course, Module, Lesson, Resource, Assignment, and Submission. Soft-deleted records are excluded from default querysets but remain accessible through the `all_objects` manager for audit and recovery purposes.
