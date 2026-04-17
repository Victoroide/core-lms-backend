# 05 -- Database Schema

> Every column below is transcribed from the corresponding
> `apps/<app>/models/*_model.py` file. Line numbers cite the model
> file. Column types reflect Django's mapping to PostgreSQL: `CharField`
> → `VARCHAR`, `TextField` → `TEXT`, `DecimalField` →
> `NUMERIC(precision, scale)`, `DateTimeField` → `TIMESTAMP WITH TIME
> ZONE`, `JSONField` → `JSONB`, `FileField` → `VARCHAR(100)` (default
> Django length) storing the S3 object key.

---

## 1. Overview

Three Django apps back the schema:

- `apps.learning`: `lms_user`, `career`, `semester`, `course`, `module`,
  `lesson`, `resource`, `evaluation`, `failed_topic`,
  `evaluation_telemetry`, `certificate`
- `apps.assessments`: `quiz`, `question`, `answer_choice`,
  `quiz_attempt`, `attempt_answer`, `proctoring_log`
- `apps.curriculum`: `assignment`, `submission`

Plus Django's built-in `auth_*`, `django_*`, and
`token_blacklist_*` tables from
`rest_framework_simplejwt.token_blacklist`
(`core_lms/settings.py:25`).

All timestamps are UTC (`USE_TZ = True`, `core_lms/settings.py:108`).

---

## 2. Table Definitions

### lms_user — `apps/learning/models/user_model.py`

Extends Django's `AbstractUser`, so the row carries all default auth
columns (`id`, `username`, `email`, `password`, `first_name`,
`last_name`, `is_active`, `is_staff`, `is_superuser`, `date_joined`,
`last_login`). Custom additions only:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| role | VARCHAR(**10**) | NO | `"STUDENT"` | Choices: `"STUDENT"`, `"TUTOR"` (user_model.py:13-27) |
| vark_dominant | VARCHAR(**15**) | NO | `"visual"` | Choices: `"visual"`, `"aural"`, `"read_write"`, `"kinesthetic"` (user_model.py:17-32) |

`AUTH_USER_MODEL = "learning.LMSUser"` (`core_lms/settings.py:96`).

---

### career — `apps/learning/models/career_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| name | VARCHAR(200) | NO | — | line 19 |
| code | VARCHAR(20) | NO | — | **UNIQUE**, line 20 |
| description | TEXT | NO | `""` | blank=True, line 21 |
| created_at | TIMESTAMPTZ | NO | now() | auto_now_add, line 22 |
| is_deleted | BOOLEAN | NO | FALSE | from `SoftDeleteMixin` |
| deleted_at | TIMESTAMPTZ | YES | NULL | from `SoftDeleteMixin` |

`Meta.ordering = ["code"]` (line 29).

---

### semester — `apps/learning/models/semester_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| career_id | BIGINT | NO | — | FK → career(id), CASCADE, line 26-30 |
| name | VARCHAR(100) | NO | — | line 31 |
| number | INTEGER | NO | — | `PositiveIntegerField`, line 32 |
| year | INTEGER | NO | — | `PositiveIntegerField`, line 33 |
| period | VARCHAR(10) | NO | `"I"` | Choices: `"I"`, `"II"`, `"SUMMER"` (lines 21-24, 34-38) |
| created_at | TIMESTAMPTZ | NO | now() | auto_now_add |
| is_deleted | BOOLEAN | NO | FALSE |  |
| deleted_at | TIMESTAMPTZ | YES | NULL |  |

**Unique constraint:** `(career_id, number, year)` (line 47).
`Meta.ordering = ["career", "number"]` (line 46).

---

### course — `apps/learning/models/course_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| semester_id | BIGINT | **YES** | NULL | FK → semester(id), **SET_NULL**, line 16-22 |
| name | VARCHAR(200) | NO | — | line 23 |
| code | VARCHAR(20) | NO | — | **UNIQUE**, line 24 |
| description | TEXT | NO | `""` | blank=True |
| created_at | TIMESTAMPTZ | NO | now() | auto_now_add |
| is_deleted | BOOLEAN | NO | FALSE |  |
| deleted_at | TIMESTAMPTZ | YES | NULL |  |

---

### module — `apps/learning/models/module_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| course_id | BIGINT | NO | — | FK → course(id), CASCADE, line 19-23 |
| title | VARCHAR(255) | NO | — | line 24 |
| description | TEXT | NO | `""` | blank=True |
| order | INTEGER | NO | 0 | `PositiveIntegerField`, line 26 |
| is_deleted | BOOLEAN | NO | FALSE |  |
| deleted_at | TIMESTAMPTZ | YES | NULL |  |

`Meta.ordering = ["course", "order"]` (line 33).

---

### lesson — `apps/learning/models/lesson_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| module_id | BIGINT | NO | — | FK → module(id), CASCADE, line 19-23 |
| title | VARCHAR(255) | NO | — | line 24 |
| content | TEXT | NO | `""` | blank=True, line 25 |
| order | INTEGER | NO | 0 | `PositiveIntegerField` |
| is_deleted | BOOLEAN | NO | FALSE |  |
| deleted_at | TIMESTAMPTZ | YES | NULL |  |

---

### resource — `apps/learning/models/resource_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| lesson_id | BIGINT | NO | — | FK → lesson(id), CASCADE (lines 30-34) |
| uploaded_by_id | BIGINT | **YES** | NULL | FK → lms_user(id), **SET_NULL** (lines 35-41) |
| file | VARCHAR(100) | NO | — | S3 object key; `upload_to=resource_upload_path` (line 42) |
| resource_type | VARCHAR(10) | NO | `"OTHER"` | Choices: `PDF`, `VIDEO`, `DOCUMENT`, `IMAGE`, `OTHER` (lines 23-28, 43-47) |
| title | VARCHAR(255) | NO | `""` | blank=True, default="" (line 48) |
| created_at | TIMESTAMPTZ | NO | now() | auto_now_add |
| is_deleted | BOOLEAN | NO | FALSE |  |
| deleted_at | TIMESTAMPTZ | YES | NULL |  |

`Meta.ordering = ["-created_at"]` (line 56).

---

### evaluation — `apps/learning/models/evaluation_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| student_id | BIGINT | NO | — | FK → lms_user(id), CASCADE (lines 16-20) |
| course_id | BIGINT | NO | — | FK → course(id), CASCADE (lines 21-25) |
| score | NUMERIC(6,2) | NO | — | line 26 |
| max_score | NUMERIC(6,2) | NO | — | line 27 |
| created_at | TIMESTAMPTZ | NO | now() | auto_now_add |

No soft-delete. `Meta.ordering = ["-created_at"]` (line 32).

---

### failed_topic — `apps/learning/models/failed_topic_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| evaluation_id | BIGINT | NO | — | FK → evaluation(id), CASCADE (lines 9-13) |
| concept_id | VARCHAR(100) | NO | — | node name in AxiomEngine graph (line 14) |
| score | NUMERIC(6,2) | NO | — | line 15 |
| max_score | NUMERIC(6,2) | NO | — | line 16 |

---

### evaluation_telemetry — `apps/learning/models/telemetry_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| evaluation_id | BIGINT | NO | — | **OneToOne FK → evaluation(id)**, CASCADE (lines 7-11), schema-level UNIQUE |
| time_on_task_seconds | INTEGER | NO | 0 | `PositiveIntegerField`, line 12 |
| clicks | INTEGER | NO | 0 | `PositiveIntegerField`, line 13 |

One telemetry row per evaluation, enforced by the OneToOne unique index.

---

### certificate — `apps/learning/models/certificate_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| student_id | BIGINT | NO | — | FK → lms_user(id), CASCADE (lines 11-15) |
| course_id | BIGINT | NO | — | FK → course(id), CASCADE (lines 16-20) |
| issued_at | TIMESTAMPTZ | NO | now() | auto_now_add (line 21) |
| certificate_hash | VARCHAR(64) | NO | `""` | **UNIQUE**, editable=False, blank=True (lines 22-28) |

**Unique constraint:** `(student_id, course_id)` (line 32).
`Meta.ordering = ["-issued_at"]` (line 33).

---

### quiz — `apps/assessments/models/quiz_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| course_id | BIGINT | NO | — | FK → course(id), CASCADE (lines 7-11) |
| title | VARCHAR(255) | NO | — | line 12 |
| description | TEXT | NO | `""` | blank=True |
| time_limit_minutes | INTEGER | NO | 30 | `PositiveIntegerField`, line 14 |
| is_active | BOOLEAN | NO | TRUE | line 15 |
| created_at | TIMESTAMPTZ | NO | now() | auto_now_add |

`Meta.ordering = ["-created_at"]` (line 21).

---

### question — `apps/assessments/models/quiz_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| quiz_id | BIGINT | NO | — | FK → quiz(id), CASCADE (lines 33-37) |
| text | TEXT | NO | — | line 38 |
| concept_id | VARCHAR(100) | NO | — | Maps to an AxiomEngine knowledge-graph node (lines 39-42) |
| order | INTEGER | NO | 0 | `PositiveIntegerField` |

`Meta.ordering = ["order"]` (line 47).

---

### answer_choice — `apps/assessments/models/quiz_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| question_id | BIGINT | NO | — | FK → question(id), CASCADE (lines 58-62) |
| text | VARCHAR(500) | NO | — | line 63 |
| is_correct | BOOLEAN | NO | FALSE | line 64 |

> `is_correct` is **never** exposed through the public API. The
> `AnswerChoiceSerializer` at `apps/assessments/serializers/quiz_serializer.py:6-11`
> uses `fields = ("id", "text")` only.

---

### quiz_attempt — `apps/assessments/models/attempt_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| student_id | BIGINT | NO | — | FK → lms_user(id), CASCADE (lines 14-18) |
| quiz_id | BIGINT | NO | — | FK → quiz(id), CASCADE (lines 19-23) |
| start_time | TIMESTAMPTZ | NO | now() | auto_now_add (line 24) |
| end_time | TIMESTAMPTZ | YES | NULL | line 25 |
| final_score | NUMERIC(6,2) | YES | NULL | lines 26-28 |
| is_submitted | BOOLEAN | NO | FALSE | line 29 |
| adaptive_plan | JSONB | YES | NULL | Stored AxiomEngine response or fallback envelope (line 30) |

`Meta.ordering = ["-start_time"]` (line 33).

---

### attempt_answer — `apps/assessments/models/attempt_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| attempt_id | BIGINT | NO | — | FK → quiz_attempt(id), CASCADE (lines 45-49) |
| question_id | BIGINT | NO | — | FK → question(id), CASCADE (lines 50-54) |
| selected_choice_id | BIGINT | NO | — | FK → answer_choice(id), CASCADE (lines 55-59) |

**Unique constraint:** `(attempt_id, question_id)` (line 62).

---

### proctoring_log — `apps/assessments/models/proctoring_model.py`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| attempt_id | BIGINT | NO | — | FK → quiz_attempt(id), CASCADE (lines 15-19) |
| event_type | VARCHAR(**25**) | NO | — | Choices: `"tab_switched"`, `"face_not_detected"`, `"multiple_faces"` (lines 10-13, 20-23) |
| timestamp | TIMESTAMPTZ | NO | — | line 24 |
| severity_score | NUMERIC(4,2) | NO | 1.00 | line 25-27 |

`Meta.ordering = ["timestamp"]` (line 31).

---

### assignment — `apps/curriculum/models/assignment_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| lesson_id | BIGINT | NO | — | FK → lesson(id), CASCADE (lines 23-27) |
| created_by_id | BIGINT | **YES** | NULL | FK → lms_user(id), **SET_NULL** (lines 28-34) |
| title | VARCHAR(255) | NO | — | line 35 |
| description | TEXT | NO | `""` | blank=True |
| due_date | TIMESTAMPTZ | YES | NULL | line 37 |
| max_score | NUMERIC(6,2) | NO | 100 | line 38 |
| created_at | TIMESTAMPTZ | NO | now() | auto_now_add |
| is_deleted | BOOLEAN | NO | FALSE |  |
| deleted_at | TIMESTAMPTZ | YES | NULL |  |

`Meta.ordering = ["-created_at"]` (line 47).

---

### submission — `apps/curriculum/models/submission_model.py` (soft-delete)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | BIGINT | NO | auto | PK |
| assignment_id | BIGINT | NO | — | FK → assignment(id), CASCADE (lines 23-27) |
| student_id | BIGINT | NO | — | FK → lms_user(id), CASCADE (lines 28-32) |
| file | VARCHAR(100) | NO | — | S3 object key; `upload_to=submission_upload_path` (line 33) |
| submitted_at | TIMESTAMPTZ | NO | now() | auto_now_add (line 34) |
| grade | NUMERIC(6,2) | YES | NULL | lines 35-37 |
| graded_at | TIMESTAMPTZ | YES | NULL | line 38 |
| is_deleted | BOOLEAN | NO | FALSE |  |
| deleted_at | TIMESTAMPTZ | YES | NULL |  |

**Unique constraint:** `(assignment_id, student_id)` (line 46).
`Meta.ordering = ["-submitted_at"]` (line 45).

---

## 3. Entity Relationship Summary

```
career 1 → * semester 1 → * course 1 → * module 1 → * lesson 1 → * resource
                              |                         |
                              |                         +─→ * assignment 1 → * submission
                              |
                              +─→ * quiz 1 → * question 1 → * answer_choice
                              |
                              +─→ * evaluation 1 → * failed_topic
                              |                  \
                              |                   +─1 evaluation_telemetry (OneToOne)
                              |
                              +─→ * certificate

quiz_attempt  * → 1 quiz       (CASCADE)
quiz_attempt  * → 1 lms_user   (CASCADE, as student)
quiz_attempt  1 → * attempt_answer
quiz_attempt  1 → * proctoring_log

attempt_answer * → 1 question        (CASCADE)
attempt_answer * → 1 answer_choice   (CASCADE)

evaluation    * → 1 lms_user   (CASCADE, as student)
certificate   * → 1 lms_user   (CASCADE, as student)
submission    * → 1 lms_user   (CASCADE, as student)
assignment    * → 1 lms_user   (SET_NULL, as created_by)
resource      * → 1 lms_user   (SET_NULL, as uploaded_by)
```

---

## 4. Soft-delete Policy

Eight models include `is_deleted` and `deleted_at`:

1. career
2. semester
3. course
4. module
5. lesson
6. resource
7. assignment
8. submission

All use `SoftDeleteMixin` with two managers (`core_lms/mixins.py`):
- `objects = SoftDeleteManager()` — filters `is_deleted=False`
  automatically.
- `all_objects = AllObjectsManager()` — returns every row.

`instance.delete()` sets `is_deleted=True` and
`deleted_at = now()` rather than issuing SQL `DELETE`.
`instance.hard_delete()` is available for real deletion (see
`core_lms/mixins.py`).

---

## 5. Migration Policy

- Migrations live in `apps/<app>/migrations/` and are committed to git.
- Production applies migrations as a separate step before
  starting the app container. The production `Dockerfile:20` does
  **not** run `migrate` — it runs `collectstatic` then `gunicorn`. See
  `08_deployment.md`.
- `test` environment (`DJANGO_ENV=test`) targets the Docker Postgres
  service and applies migrations on test-runner startup (standard
  Django behavior).
