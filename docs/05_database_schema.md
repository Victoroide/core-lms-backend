# 05 -- Database Schema

> PUDS -- AxiomLMS Database Schema Reference
> Version 1.0 | 2026-04-16

---

## 1. Overview

The AxiomLMS database runs on PostgreSQL (NeonDB serverless in production, Docker ephemeral for development and CI). The schema spans three Django apps -- `learning`, `assessments`, and `curriculum` -- totaling 19 application tables plus Django's built-in auth and admin tables.

All timestamps are stored in UTC. All `VARCHAR` lengths are specified as maximum character counts. `DECIMAL` types use the notation `DECIMAL(precision, scale)`.

---

## 2. Table Definitions

### lms_user

Extends Django's built-in `auth_user` table via a one-to-one relationship or custom user model. Contains additional fields for the LMS domain.

| Column         | Type          | Nullable | Default | Constraints                          |
|----------------|---------------|----------|---------|--------------------------------------|
| id             | INTEGER       | NO       | auto    | PRIMARY KEY                          |
| role           | VARCHAR(7)    | NO       |         | Choices: student, tutor              |
| vark_dominant  | VARCHAR(10)   | YES      | NULL    | VARK learning style (V, A, R, K)     |
| (inherited)    |               |          |         | All fields from Django auth_user     |

Note: The `lms_user` table inherits all columns from Django's `auth_user` model, including `username`, `email`, `password`, `first_name`, `last_name`, `is_active`, `is_staff`, `is_superuser`, `date_joined`, and `last_login`.

---

### career

| Column      | Type          | Nullable | Default | Constraints           |
|-------------|---------------|----------|---------|-----------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY           |
| name        | VARCHAR(200)  | NO       |         |                       |
| code        | VARCHAR(20)   | NO       |         | UNIQUE                |
| description | TEXT          | NO       |         |                       |
| created_at  | TIMESTAMP     | NO       | now()   |                       |
| is_deleted  | BOOLEAN       | NO       | FALSE   |                       |
| deleted_at  | TIMESTAMP     | YES      | NULL    |                       |

---

### semester

| Column      | Type          | Nullable | Default | Constraints                              |
|-------------|---------------|----------|---------|------------------------------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY                              |
| career_id   | INTEGER       | NO       |         | FOREIGN KEY -> career(id)                |
| name        | VARCHAR(100)  | NO       |         |                                          |
| number      | INTEGER       | NO       |         |                                          |
| year        | INTEGER       | NO       |         |                                          |
| period      | VARCHAR(6)    | NO       |         |                                          |
| created_at  | TIMESTAMP     | NO       | now()   |                                          |
| is_deleted  | BOOLEAN       | NO       | FALSE   |                                          |
| deleted_at  | TIMESTAMP     | YES      | NULL    |                                          |

**Unique constraint:** `(career_id, number, year)`

---

### course

| Column      | Type          | Nullable | Default | Constraints                    |
|-------------|---------------|----------|---------|--------------------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY                    |
| semester_id | INTEGER       | YES      | NULL    | FOREIGN KEY -> semester(id)    |
| name        | VARCHAR(200)  | NO       |         |                                |
| code        | VARCHAR(20)   | NO       |         | UNIQUE                         |
| description | TEXT          | NO       |         |                                |
| created_at  | TIMESTAMP     | NO       | now()   |                                |
| is_deleted  | BOOLEAN       | NO       | FALSE   |                                |
| deleted_at  | TIMESTAMP     | YES      | NULL    |                                |

---

### module

| Column      | Type          | Nullable | Default | Constraints                   |
|-------------|---------------|----------|---------|-------------------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY                   |
| course_id   | INTEGER       | NO       |         | FOREIGN KEY -> course(id)     |
| title       | VARCHAR(200)  | NO       |         |                               |
| description | TEXT          | NO       |         |                               |
| order       | INTEGER       | NO       |         |                               |
| is_deleted  | BOOLEAN       | NO       | FALSE   |                               |
| deleted_at  | TIMESTAMP     | YES      | NULL    |                               |

---

### lesson

| Column      | Type          | Nullable | Default | Constraints                   |
|-------------|---------------|----------|---------|-------------------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY                   |
| module_id   | INTEGER       | NO       |         | FOREIGN KEY -> module(id)     |
| title       | VARCHAR(200)  | NO       |         |                               |
| content     | TEXT          | NO       |         |                               |
| order       | INTEGER       | NO       |         |                               |
| is_deleted  | BOOLEAN       | NO       | FALSE   |                               |
| deleted_at  | TIMESTAMP     | YES      | NULL    |                               |

---

### resource

| Column         | Type          | Nullable | Default | Constraints                      |
|----------------|---------------|----------|---------|----------------------------------|
| id             | INTEGER       | NO       | auto    | PRIMARY KEY                      |
| lesson_id      | INTEGER       | NO       |         | FOREIGN KEY -> lesson(id)        |
| uploaded_by_id | INTEGER       | YES      | NULL    | FOREIGN KEY -> lms_user(id)      |
| file           | VARCHAR(100)  | NO       |         | File path (S3 storage backend)   |
| resource_type  | VARCHAR(10)   | NO       |         | e.g., pdf, image, video          |
| title          | VARCHAR(255)  | NO       |         |                                  |
| created_at     | TIMESTAMP     | NO       | now()   |                                  |
| is_deleted     | BOOLEAN       | NO       | FALSE   |                                  |
| deleted_at     | TIMESTAMP     | YES      | NULL    |                                  |

---

### evaluation

| Column      | Type          | Nullable | Default | Constraints                      |
|-------------|---------------|----------|---------|----------------------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY                      |
| student_id  | INTEGER       | NO       |         | FOREIGN KEY -> lms_user(id)      |
| course_id   | INTEGER       | NO       |         | FOREIGN KEY -> course(id)        |
| score       | DECIMAL(6,2)  | NO       |         |                                  |
| max_score   | DECIMAL(6,2)  | NO       |         |                                  |
| created_at  | TIMESTAMP     | NO       | now()   |                                  |

---

### failed_topic

| Column        | Type          | Nullable | Default | Constraints                         |
|---------------|---------------|----------|---------|-------------------------------------|
| id            | INTEGER       | NO       | auto    | PRIMARY KEY                         |
| evaluation_id | INTEGER       | NO       |         | FOREIGN KEY -> evaluation(id)       |
| concept_id    | VARCHAR(100)  | NO       |         |                                     |
| score         | DECIMAL(6,2)  | NO       |         |                                     |
| max_score     | DECIMAL(6,2)  | NO       |         |                                     |

---

### evaluation_telemetry

| Column               | Type          | Nullable | Default | Constraints                                     |
|----------------------|---------------|----------|---------|-------------------------------------------------|
| id                   | INTEGER       | NO       | auto    | PRIMARY KEY                                     |
| evaluation_id        | INTEGER       | NO       |         | FOREIGN KEY -> evaluation(id), UNIQUE (OneToOne)|
| time_on_task_seconds | INTEGER       | NO       |         |                                                 |
| clicks               | INTEGER       | NO       |         |                                                 |

**Relationship:** One-to-one with `evaluation`. Each evaluation has at most one telemetry record.

---

### certificate

| Column           | Type          | Nullable | Default | Constraints                      |
|------------------|---------------|----------|---------|----------------------------------|
| id               | INTEGER       | NO       | auto    | PRIMARY KEY                      |
| student_id       | INTEGER       | NO       |         | FOREIGN KEY -> lms_user(id)      |
| course_id        | INTEGER       | NO       |         | FOREIGN KEY -> course(id)        |
| issued_at        | TIMESTAMP     | NO       | now()   |                                  |
| certificate_hash | VARCHAR(64)   | NO       |         | UNIQUE (SHA-256 hex digest)      |

**Unique constraint:** `(student_id, course_id)` -- A student can hold at most one certificate per course.

---

### quiz

| Column             | Type          | Nullable | Default | Constraints                   |
|--------------------|---------------|----------|---------|-------------------------------|
| id                 | INTEGER       | NO       | auto    | PRIMARY KEY                   |
| course_id          | INTEGER       | NO       |         | FOREIGN KEY -> course(id)     |
| title              | VARCHAR(200)  | NO       |         |                               |
| description        | TEXT          | NO       |         |                               |
| time_limit_minutes | INTEGER       | NO       |         |                               |
| is_active          | BOOLEAN       | NO       | TRUE    |                               |
| created_at         | TIMESTAMP     | NO       | now()   |                               |

---

### question

| Column      | Type          | Nullable | Default | Constraints                   |
|-------------|---------------|----------|---------|-------------------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY                   |
| quiz_id     | INTEGER       | NO       |         | FOREIGN KEY -> quiz(id)       |
| text        | TEXT          | NO       |         |                               |
| concept_id  | VARCHAR(100)  | NO       |         |                               |
| order       | INTEGER       | NO       |         |                               |

---

### answer_choice

| Column      | Type          | Nullable | Default | Constraints                    |
|-------------|---------------|----------|---------|--------------------------------|
| id          | INTEGER       | NO       | auto    | PRIMARY KEY                    |
| question_id | INTEGER       | NO       |         | FOREIGN KEY -> question(id)    |
| text        | VARCHAR(500)  | NO       |         |                                |
| is_correct  | BOOLEAN       | NO       | FALSE   |                                |

---

### quiz_attempt

| Column        | Type          | Nullable | Default | Constraints                      |
|---------------|---------------|----------|---------|----------------------------------|
| id            | INTEGER       | NO       | auto    | PRIMARY KEY                      |
| student_id    | INTEGER       | NO       |         | FOREIGN KEY -> lms_user(id)      |
| quiz_id       | INTEGER       | NO       |         | FOREIGN KEY -> quiz(id)          |
| start_time    | TIMESTAMP     | NO       | now()   |                                  |
| end_time      | TIMESTAMP     | YES      | NULL    |                                  |
| final_score   | DECIMAL(6,2)  | YES      | NULL    |                                  |
| is_submitted  | BOOLEAN       | NO       | FALSE   |                                  |
| adaptive_plan | JSONB         | YES      | NULL    | Stored AxiomEngine response      |

---

### attempt_answer

| Column             | Type          | Nullable | Default | Constraints                          |
|--------------------|---------------|----------|---------|--------------------------------------|
| id                 | INTEGER       | NO       | auto    | PRIMARY KEY                          |
| attempt_id         | INTEGER       | NO       |         | FOREIGN KEY -> quiz_attempt(id)      |
| question_id        | INTEGER       | NO       |         | FOREIGN KEY -> question(id)          |
| selected_choice_id | INTEGER       | NO       |         | FOREIGN KEY -> answer_choice(id)     |

**Unique constraint:** `(attempt_id, question_id)` -- A student can answer each question at most once per attempt.

---

### proctoring_log

| Column         | Type          | Nullable | Default | Constraints                          |
|----------------|---------------|----------|---------|--------------------------------------|
| id             | INTEGER       | NO       | auto    | PRIMARY KEY                          |
| attempt_id     | INTEGER       | NO       |         | FOREIGN KEY -> quiz_attempt(id)      |
| event_type     | VARCHAR(20)   | NO       |         | e.g., tab_switch, face_absence       |
| timestamp      | TIMESTAMP     | NO       |         |                                      |
| severity_score | DECIMAL(3,2)  | NO       |         | Range 0.00 to 1.00                   |

---

### assignment

| Column        | Type          | Nullable | Default | Constraints                      |
|---------------|---------------|----------|---------|----------------------------------|
| id            | INTEGER       | NO       | auto    | PRIMARY KEY                      |
| lesson_id     | INTEGER       | NO       |         | FOREIGN KEY -> lesson(id)        |
| created_by_id | INTEGER       | YES      | NULL    | FOREIGN KEY -> lms_user(id)      |
| title         | VARCHAR(255)  | NO       |         |                                  |
| description   | TEXT          | NO       |         |                                  |
| due_date      | TIMESTAMP     | YES      | NULL    |                                  |
| max_score     | DECIMAL(6,2)  | NO       |         |                                  |
| created_at    | TIMESTAMP     | NO       | now()   |                                  |
| is_deleted    | BOOLEAN       | NO       | FALSE   |                                  |
| deleted_at    | TIMESTAMP     | YES      | NULL    |                                  |

---

### submission

| Column        | Type          | Nullable | Default | Constraints                        |
|---------------|---------------|---------|---------|------------------------------------|
| id            | INTEGER       | NO       | auto    | PRIMARY KEY                        |
| assignment_id | INTEGER       | NO       |         | FOREIGN KEY -> assignment(id)      |
| student_id    | INTEGER       | NO       |         | FOREIGN KEY -> lms_user(id)        |
| file          | VARCHAR(100)  | NO       |         | File path (S3 storage backend)     |
| submitted_at  | TIMESTAMP     | NO       | now()   |                                    |
| grade         | DECIMAL(6,2)  | YES      | NULL    |                                    |
| graded_at     | TIMESTAMP     | YES      | NULL    |                                    |
| is_deleted    | BOOLEAN       | NO       | FALSE   |                                    |
| deleted_at    | TIMESTAMP     | YES      | NULL    |                                    |

**Unique constraint:** `(assignment_id, student_id)` -- A student can submit at most once per assignment.

---

## 3. Entity Relationship Summary

```
career 1---* semester 1---* course 1---* module 1---* lesson 1---* resource
                                   |                          |
                                   |                          +---* assignment 1---* submission
                                   |
                                   +---* quiz 1---* question 1---* answer_choice
                                   |
                                   +---* evaluation 1---* failed_topic
                                   |              |
                                   |              +---1 evaluation_telemetry
                                   |
                                   +---* certificate

quiz_attempt *---1 quiz
quiz_attempt *---1 lms_user (student)
quiz_attempt 1---* attempt_answer
quiz_attempt 1---* proctoring_log

attempt_answer *---1 question
attempt_answer *---1 answer_choice

evaluation *---1 lms_user (student)
evaluation *---1 course

certificate *---1 lms_user (student)
certificate *---1 course

submission *---1 lms_user (student)
resource *---1 lms_user (uploaded_by)
assignment *---1 lms_user (created_by)
```

---

## 4. Soft Delete Policy

Eight models implement soft deletion:

1. `career`
2. `semester`
3. `course`
4. `module`
5. `lesson`
6. `resource`
7. `assignment`
8. `submission`

Each soft-deletable model includes two fields:

| Field       | Type       | Default | Purpose                                    |
|-------------|------------|---------|--------------------------------------------|
| is_deleted  | BOOLEAN    | FALSE   | Marks the record as logically deleted       |
| deleted_at  | TIMESTAMP  | NULL    | Records the moment of deletion              |

**Manager behavior:**

- `SoftDeleteManager` (default manager) -- Automatically appends `WHERE is_deleted = FALSE` to all querysets. This is the default manager assigned to all soft-deletable models, ensuring that application code never accidentally surfaces deleted records.
- `AllObjectsManager` -- Returns all records regardless of `is_deleted` status. Used exclusively for administrative tasks, data seeding, and migration scripts that must operate on the full dataset.

**Delete operation:** Calling `.delete()` on a soft-deletable model instance sets `is_deleted = TRUE` and `deleted_at = now()` instead of issuing a SQL `DELETE` statement. Hard deletion requires direct database access or explicit use of `AllObjectsManager`.

---

## 5. Migration Policy

- Migrations are generated via `python manage.py makemigrations` and committed to version control.
- Migrations are applied via `python manage.py migrate`.
- Production deployments run migrations as a separate step before starting the application server. The application never auto-migrates on startup in production.
- Each app maintains its own `migrations/` directory with a sequential numbering scheme.
- Backward-incompatible schema changes (column removal, type narrowing) require a multi-step migration strategy: add the new column, backfill, deploy code that uses the new column, then remove the old column in a subsequent release.
