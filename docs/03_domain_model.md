# 03 -- Domain Model

> Field names, types, constraints, and relationships are transcribed from
> `apps/*/models/*_model.py`. Line numbers cite the model file.

## 1. Class Diagram

```
+-----------------------+           +-----------------------+           +-----------------------+
|       LMSUser         |           |        Career         |           |       Semester        |
|  (AbstractUser)       |           |  (SoftDeleteMixin)    |           |  (SoftDeleteMixin)    |
|-----------------------|           |-----------------------|           |-----------------------|
| role        [10, E1]  |           | name       (200)      |           | career -> Career (CASCADE)
| vark_dominant [15, E2]|           | code   unique (20)    |           | name       (100)      |
+-----------------------+           | description TEXT      |           | number     uint       |
                                    | created_at auto       |           | year       uint       |
                                    +-----------+-----------+           | period   [10, E3]     |
                                                | 1                     | created_at auto       |
                                                | has many              +-----------+-----------+
                                                v                                   | 1
                                       +-----------------------+                    | has many
                                       |       Semester        |<-------------------+
                                       +-----------+-----------+
                                                   | 1
                                                   | has many (SET_NULL, nullable)
                                                   v
                                       +-----------------------+
                                       |        Course         |
                                       |  (SoftDeleteMixin)    |
                                       |-----------------------|
                                       | semester -> Semester (SET_NULL, nullable)
                                       | name (200), code unique (20)
                                       | description, created_at auto
                                       +-----+-----------------+---+
                                             | 1               | 1
                          +------------------+                 +---------------+
                          | has many                                   has many |
                          v                                                     v
                  +---------------+   +-----------------+    +---------------+   +------------+
                  |   Module      |   |      Quiz       |    |  Evaluation   |   | Certificate|
                  |  (SoftDel)    |   |-----------------|    |---------------|   |------------|
                  | course -> C   |   | course -> C     |    | student -> U  |   | student->U |
                  | title (255)   |   | title (255)     |    | course  -> C  |   | course ->C |
                  | description   |   | description     |    | score D(6,2)  |   | issued_at  |
                  | order uint    |   | time_limit_min  |    | max_score     |   | cert_hash  |
                  +------+--------+   | is_active       |    | created_at    |   | unique(64) |
                         | 1          | created_at      |    +------+--------+   +------------+
                         | has many   +--------+--------+           | 1
                         v                     | 1                  +---------+
                  +---------------+            | has many                     | has many
                  |   Lesson      |            v                              v
                  |  (SoftDel)    |    +--------------+            +-------------------+
                  | module -> M   |    |   Question   |            |  FailedTopic      |
                  | title (255)   |    |--------------|            |-------------------|
                  | content TEXT  |    | quiz -> Q    |            | evaluation -> Ev  |
                  | order uint    |    | text TEXT    |            | concept_id (100)  |
                  +---+------+----+    | concept_id   |            | score D(6,2)      |
                      | 1    | 1       | order uint   |            | max_score D(6,2)  |
                      |      |         +------+-------+            +-------------------+
              has many|      |has many        | 1
                      v      v                | has many         +---------------------+
            +-----------+  +-----------+      v                  | EvaluationTelemetry |
            | Resource  |  | Assignment|   +-----------+         | (OneToOne Evaluation)|
            | (SoftDel) |  | (SoftDel, |   | Answer    |         |---------------------|
            |-----------|  |  curric.) |   | Choice    |         | evaluation -> Ev    |
            | lesson->L |  |-----------|   |-----------|         | time_on_task_seconds|
            | uploaded_by->U  (SET_NULL)   | question->Q         | clicks              |
            | file      |  | lesson -> L   | text (500)          +---------------------+
            | resource_ |  | created_by->U | is_correct
            |   type E4 |  | title (255)   +-----------+
            | title(255)|  | description   |
            | created_at|  | due_date      | selected by
            +-----------+  | max_score 100 |     v
                           | created_at    | +--------------------+
                           +------+--------+ |  AttemptAnswer     |
                                  | 1        |--------------------|
                                  | has many | attempt -> QA      |
                                  v          | question -> Q      |
                           +--------------+  | selected_choice->AC|
                           |  Submission  |  | unique(attempt,Q)  |
                           | (SoftDel,    |  +---------+----------+
                           |  curric.)    |            ^
                           |--------------|            | has many
                           | assignment->A|     +-------------+
                           | student -> U |     |  QuizAttempt|
                           | file         |     |-------------|
                           | submitted_at |     | student->U  |
                           | grade null   |     | quiz -> Q   |
                           | graded_at    |     | start_time  |
                           | unique(A,U)  |     | end_time    |
                           +--------------+     | final_score |
                                                | is_submitted|
                                                | adaptive_plan JSON
                                                +------+------+
                                                       | 1
                                                       | has many
                                                       v
                                                +-----------------+
                                                | ProctoringLog   |
                                                |-----------------|
                                                | attempt -> QA   |
                                                | event_type E5   |
                                                | timestamp       |
                                                | severity_score  |
                                                +-----------------+

E1: role choices = {STUDENT, TUTOR} (user_model.py:13-15)
E2: vark_dominant choices = {visual, aural, read_write, kinesthetic} (user_model.py:17-21)
E3: period choices = {I, II, SUMMER} (semester_model.py:21-24)
E4: resource_type choices = {PDF, VIDEO, DOCUMENT, IMAGE, OTHER} (resource_model.py:23-28)
E5: event_type choices = {tab_switched, face_not_detected, multiple_faces} (proctoring_model.py:10-13)
```

### Relationship summary

```
LMSUser          1 → *  Evaluation        (student, CASCADE)
LMSUser          1 → *  Certificate       (student, CASCADE)
LMSUser          1 → *  QuizAttempt       (student, CASCADE)
LMSUser          1 → *  Resource          (uploaded_by, SET_NULL)
LMSUser          1 → *  Assignment        (created_by, SET_NULL)
LMSUser          1 → *  Submission        (student, CASCADE)

Career           1 → *  Semester          (CASCADE)
Semester         1 → *  Course            (Course.semester nullable, SET_NULL)
Course           1 → *  Module            (CASCADE)
Course           1 → *  Quiz              (CASCADE)
Course           1 → *  Evaluation        (CASCADE)
Course           1 → *  Certificate       (CASCADE)

Module           1 → *  Lesson            (CASCADE)
Lesson           1 → *  Resource          (CASCADE)
Lesson           1 → *  Assignment        (CASCADE)
Assignment       1 → *  Submission        (CASCADE)

Quiz             1 → *  Question          (CASCADE)
Question         1 → *  AnswerChoice      (CASCADE)
Quiz             1 → *  QuizAttempt       (via attempts, CASCADE)
QuizAttempt      1 → *  AttemptAnswer     (CASCADE; unique(attempt, question))
QuizAttempt      1 → *  ProctoringLog     (CASCADE)
AttemptAnswer    * → 1  Question          (CASCADE)
AttemptAnswer    * → 1  AnswerChoice      (CASCADE)

Evaluation       1 → 1  EvaluationTelemetry (CASCADE; OneToOne)
Evaluation       1 → *  FailedTopic       (CASCADE)
```

## 2. Model Descriptions (one per model file)

### LMSUser — `apps/learning/models/user_model.py`
- Extends `AbstractUser` (line 5).
- `role` — CharField(max_length=10, choices=Role.choices, default=STUDENT)
  (lines 23-27). `Role.STUDENT = "STUDENT"`, `Role.TUTOR = "TUTOR"`.
- `vark_dominant` — CharField(max_length=15, choices=VARKProfile.choices,
  default=VISUAL) (lines 28-32). Values: `"visual"`, `"aural"`,
  `"read_write"`, `"kinesthetic"`.
- `Meta.db_table = "lms_user"` (line 35).

### Career — `apps/learning/models/career_model.py`
- Fields: `name` CharField(200) (line 19); `code` CharField(20, unique=True)
  (line 20); `description` TextField(blank=True, default="") (line 21);
  `created_at` DateTimeField(auto_now_add=True) (line 22).
- Managers: `objects = SoftDeleteManager()`,
  `all_objects = AllObjectsManager()` (lines 24-25).
- `Meta.db_table = "career"`, `ordering = ["code"]` (lines 28-29).

### Semester — `apps/learning/models/semester_model.py`
- `career` — FK→Career, on_delete=CASCADE, related_name="semesters"
  (lines 26-30).
- `name` CharField(100) (line 31); `number` PositiveIntegerField (line 32);
  `year` PositiveIntegerField (line 33); `period` CharField(max_length=10,
  choices, default=FIRST) (line 34-38) with values `I`, `II`, `SUMMER`;
  `created_at` auto (line 39).
- `Meta.unique_together = [("career", "number", "year")]` (line 47).

### Course — `apps/learning/models/course_model.py`
- `semester` — FK→Semester, **nullable**, on_delete=SET_NULL (lines 16-22).
- `name` CharField(200) (line 23); `code` CharField(20, unique=True)
  (line 24); `description` TextField(blank=True, default="") (line 25);
  `created_at` auto (line 26).

### Module — `apps/learning/models/module_model.py`
- `course` — FK→Course, on_delete=CASCADE, related_name="modules"
  (lines 19-23).
- `title` CharField(255) (line 24); `description` TextField (line 25);
  `order` PositiveIntegerField(default=0) (line 26).

### Lesson — `apps/learning/models/lesson_model.py`
- `module` — FK→Module, on_delete=CASCADE, related_name="lessons"
  (lines 19-23).
- `title` CharField(255) (line 24); `content` TextField (line 25);
  `order` PositiveIntegerField(default=0) (line 26).

### Resource — `apps/learning/models/resource_model.py`
- `lesson` — FK→Lesson, CASCADE (lines 30-34).
- `uploaded_by` — FK→AUTH_USER_MODEL, SET_NULL, nullable (lines 35-41).
- `file` — FileField(upload_to=resource_upload_path) (line 42) where
  `resource_upload_path` returns
  `f"resources/{instance.lesson.module.course_id}/{filename}"`
  (`apps/learning/services/storage_service.py:4-14`).
- `resource_type` — CharField(max_length=10, choices) (lines 43-47):
  `PDF`, `VIDEO`, `DOCUMENT`, `IMAGE`, `OTHER` (lines 23-28).
- `title` CharField(255, blank=True, default="") (line 48); `created_at`
  auto (line 49).

### Evaluation — `apps/learning/models/evaluation_model.py`
- `student` — FK→AUTH_USER_MODEL, CASCADE (lines 16-20).
- `course` — FK→Course, CASCADE (lines 21-25).
- `score` DecimalField(max_digits=6, decimal_places=2) (line 26);
  `max_score` DecimalField(6,2) (line 27); `created_at` auto (line 28).
- No soft-delete mixin.

### FailedTopic — `apps/learning/models/failed_topic_model.py`
- `evaluation` — FK→Evaluation, CASCADE, related_name="failed_topics"
  (lines 9-13).
- `concept_id` CharField(100) (line 14) — must match a node name in the
  AxiomEngine knowledge graph (see `04_architecture.md` § 2.2).
- `score` / `max_score` DecimalField(6,2) (lines 15-16).

### EvaluationTelemetry — `apps/learning/models/telemetry_model.py`
- `evaluation` — **OneToOneField**→Evaluation, CASCADE,
  related_name="telemetry" (lines 7-11).
- `time_on_task_seconds` PositiveIntegerField(default=0) (line 12);
  `clicks` PositiveIntegerField(default=0) (line 13).

### Certificate — `apps/learning/models/certificate_model.py`
- `student` — FK→AUTH_USER_MODEL, CASCADE (lines 11-15).
- `course` — FK→Course, CASCADE (lines 16-20).
- `issued_at` DateTimeField(auto_now_add=True) (line 21).
- `certificate_hash` CharField(max_length=64, unique=True, editable=False,
  blank=True, default="") (lines 22-28).
- `Meta.unique_together = [("student", "course")]`,
  `ordering = ["-issued_at"]` (lines 32-33).

### Quiz — `apps/assessments/models/quiz_model.py`
- `course` — FK→Course, CASCADE, related_name="quizzes" (lines 7-11).
- `title` CharField(255) (line 12); `description` TextField (line 13);
  `time_limit_minutes` PositiveIntegerField(default=30) (line 14);
  `is_active` BooleanField(default=True) (line 15); `created_at` auto.
- `Meta.db_table = "quiz"`, `verbose_name_plural = "Quizzes"`,
  `ordering = ["-created_at"]` (lines 18-21).

### Question — `apps/assessments/models/quiz_model.py`
- `quiz` — FK→Quiz, CASCADE, related_name="questions" (lines 33-37).
- `text` TextField (line 38); `concept_id` CharField(100) with
  `help_text="Must match a node name in the AxiomEngine knowledge graph."`
  (lines 39-42); `order` PositiveIntegerField(default=0) (line 43).

### AnswerChoice — `apps/assessments/models/quiz_model.py`
- `question` — FK→Question, CASCADE, related_name="choices" (lines 58-62).
- `text` CharField(500) (line 63); `is_correct` BooleanField(default=False)
  (line 64). `is_correct` is **never** exposed in the public `AnswerChoiceSerializer`
  (`apps/assessments/serializers/quiz_serializer.py:6-11`).

### QuizAttempt — `apps/assessments/models/attempt_model.py`
- `student` — FK→AUTH_USER_MODEL, CASCADE (lines 14-18).
- `quiz` — FK→Quiz, CASCADE (lines 19-23).
- `start_time` auto (line 24); `end_time` nullable (line 25);
  `final_score` DecimalField(6,2, nullable) (lines 26-28);
  `is_submitted` BooleanField(default=False) (line 29);
  `adaptive_plan` JSONField(nullable) (line 30).

### AttemptAnswer — `apps/assessments/models/attempt_model.py`
- `attempt` — FK→QuizAttempt, CASCADE, related_name="answers"
  (lines 45-49).
- `question` — FK→Question, CASCADE (lines 50-54).
- `selected_choice` — FK→AnswerChoice, CASCADE (lines 55-59).
- `Meta.unique_together = [("attempt", "question")]` (line 62).

### ProctoringLog — `apps/assessments/models/proctoring_model.py`
- `attempt` — FK→QuizAttempt, CASCADE,
  related_name="proctoring_logs" (lines 15-19).
- `event_type` CharField(max_length=25, choices) (lines 20-23) with
  values `tab_switched`, `face_not_detected`, `multiple_faces` (lines 10-13).
- `timestamp` DateTimeField (line 24).
- `severity_score` DecimalField(max_digits=4, decimal_places=2,
  default=1.00) (lines 25-27).

### Assignment — `apps/curriculum/models/assignment_model.py`
- Extends `SoftDeleteMixin, models.Model` (line 7).
- `lesson` — FK→Lesson, CASCADE, related_name="assignments"
  (lines 23-27).
- `created_by` — FK→AUTH_USER_MODEL, SET_NULL, nullable (lines 28-34).
- `title` CharField(255) (line 35); `description` TextField (line 36);
  `due_date` DateTimeField(nullable) (line 37); `max_score` DecimalField(6,2,
  default=100) (line 38); `created_at` auto (line 39).
- `Meta.db_table = "assignment"`,
  `ordering = ["-created_at"]` (lines 44-48).

### Submission — `apps/curriculum/models/submission_model.py`
- Extends `SoftDeleteMixin, models.Model` (line 8).
- `assignment` — FK→Assignment, CASCADE,
  related_name="submissions" (lines 23-27).
- `student` — FK→AUTH_USER_MODEL, CASCADE,
  related_name="submissions" (lines 28-32).
- `file` — FileField(upload_to=submission_upload_path) (line 33).
  `submission_upload_path` returns
  `f"submissions/{instance.student_id}/{filename}"`
  (`apps/curriculum/services/storage_service.py:4-14`).
- `submitted_at` auto (line 34); `grade` DecimalField(6,2, nullable)
  (lines 35-37); `graded_at` DateTimeField(nullable) (line 38).
- `Meta.unique_together = [("assignment", "student")]` (line 46).
