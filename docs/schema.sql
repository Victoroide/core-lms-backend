-- Database: AxiomLMS (NeonDB)
-- Engine: PostgreSQL 15+
-- Generated Date: 2026-04-25

DROP TABLE IF EXISTS certificate CASCADE;
DROP TABLE IF EXISTS evaluation_telemetry CASCADE;
DROP TABLE IF EXISTS failed_topic CASCADE;
DROP TABLE IF EXISTS evaluation CASCADE;
DROP TABLE IF EXISTS proctoring_log CASCADE;
DROP TABLE IF EXISTS attempt_answer CASCADE;
DROP TABLE IF EXISTS quiz_attempt CASCADE;
DROP TABLE IF EXISTS answer_choice CASCADE;
DROP TABLE IF EXISTS question CASCADE;
DROP TABLE IF EXISTS quiz CASCADE;
DROP TABLE IF EXISTS submission CASCADE;
DROP TABLE IF EXISTS assignment CASCADE;
DROP TABLE IF EXISTS resource CASCADE;
DROP TABLE IF EXISTS lesson CASCADE;
DROP TABLE IF EXISTS module CASCADE;
DROP TABLE IF EXISTS course CASCADE;
DROP TABLE IF EXISTS semester CASCADE;
DROP TABLE IF EXISTS career CASCADE;
DROP TABLE IF EXISTS lms_user CASCADE;

-- ==========================================
-- APP: learning (Core Identity & Ontology)
-- ==========================================

-- Note: lms_user extends Django's AbstractUser. We merge all base fields here.
CREATE TABLE lms_user (
    id BIGSERIAL NOT NULL,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    role VARCHAR(10) NOT NULL DEFAULT 'STUDENT',
    vark_dominant VARCHAR(15) NOT NULL DEFAULT 'visual',
    CONSTRAINT pk_lms_user PRIMARY KEY (id),
    CONSTRAINT uk_lms_user_username UNIQUE (username)
);

CREATE TABLE career (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(20) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_career PRIMARY KEY (id),
    CONSTRAINT uk_career_code UNIQUE (code)
);

CREATE TABLE semester (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(100) NOT NULL,
    number INTEGER NOT NULL,
    year INTEGER NOT NULL,
    period VARCHAR(10) NOT NULL DEFAULT 'I',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    career_id BIGINT NOT NULL,
    CONSTRAINT pk_semester PRIMARY KEY (id),
    CONSTRAINT fk_semester_career FOREIGN KEY (career_id) REFERENCES career(id) ON DELETE CASCADE,
    CONSTRAINT uk_semester_career_number_year UNIQUE (career_id, number, year)
);

CREATE TABLE course (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(20) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    semester_id BIGINT,
    CONSTRAINT pk_course PRIMARY KEY (id),
    CONSTRAINT fk_course_semester FOREIGN KEY (semester_id) REFERENCES semester(id) ON DELETE SET NULL,
    CONSTRAINT uk_course_code UNIQUE (code)
);

CREATE TABLE module (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    order INTEGER NOT NULL DEFAULT 0,
    course_id BIGINT NOT NULL,
    CONSTRAINT pk_module PRIMARY KEY (id),
    CONSTRAINT fk_module_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
);

CREATE TABLE lesson (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    order INTEGER NOT NULL DEFAULT 0,
    module_id BIGINT NOT NULL,
    CONSTRAINT pk_lesson PRIMARY KEY (id),
    CONSTRAINT fk_lesson_module FOREIGN KEY (module_id) REFERENCES module(id) ON DELETE CASCADE
);

CREATE TABLE resource (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    file VARCHAR(100) NOT NULL,
    resource_type VARCHAR(10) NOT NULL DEFAULT 'OTHER',
    title VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lesson_id BIGINT NOT NULL,
    uploaded_by_id BIGINT,
    CONSTRAINT pk_resource PRIMARY KEY (id),
    CONSTRAINT fk_resource_lesson FOREIGN KEY (lesson_id) REFERENCES lesson(id) ON DELETE CASCADE,
    CONSTRAINT fk_resource_uploaded_by FOREIGN KEY (uploaded_by_id) REFERENCES lms_user(id) ON DELETE SET NULL
);

-- ==========================================
-- APP: curriculum (Assignments & Submissions)
-- ==========================================

CREATE TABLE assignment (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    due_date TIMESTAMPTZ,
    max_score DECIMAL(6,2) NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lesson_id BIGINT NOT NULL,
    created_by_id BIGINT,
    CONSTRAINT pk_assignment PRIMARY KEY (id),
    CONSTRAINT fk_assignment_lesson FOREIGN KEY (lesson_id) REFERENCES lesson(id) ON DELETE CASCADE,
    CONSTRAINT fk_assignment_created_by FOREIGN KEY (created_by_id) REFERENCES lms_user(id) ON DELETE SET NULL
);

CREATE TABLE submission (
    id BIGSERIAL NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    file VARCHAR(100) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    grade DECIMAL(6,2),
    graded_at TIMESTAMPTZ,
    assignment_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    CONSTRAINT pk_submission PRIMARY KEY (id),
    CONSTRAINT fk_submission_assignment FOREIGN KEY (assignment_id) REFERENCES assignment(id) ON DELETE CASCADE,
    CONSTRAINT fk_submission_student FOREIGN KEY (student_id) REFERENCES lms_user(id) ON DELETE CASCADE,
    CONSTRAINT uk_submission_assignment_student UNIQUE (assignment_id, student_id)
);

-- ==========================================
-- APP: assessments (Quizzes & Proctoring)
-- ==========================================

CREATE TABLE quiz (
    id BIGSERIAL NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    time_limit_minutes INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    course_id BIGINT NOT NULL,
    CONSTRAINT pk_quiz PRIMARY KEY (id),
    CONSTRAINT fk_quiz_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
);

CREATE TABLE question (
    id BIGSERIAL NOT NULL,
    text TEXT NOT NULL,
    concept_id VARCHAR(100) NOT NULL,
    order INTEGER NOT NULL DEFAULT 0,
    quiz_id BIGINT NOT NULL,
    CONSTRAINT pk_question PRIMARY KEY (id),
    CONSTRAINT fk_question_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(id) ON DELETE CASCADE
);

CREATE TABLE answer_choice (
    id BIGSERIAL NOT NULL,
    text VARCHAR(500) NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    question_id BIGINT NOT NULL,
    CONSTRAINT pk_answer_choice PRIMARY KEY (id),
    CONSTRAINT fk_answer_choice_question FOREIGN KEY (question_id) REFERENCES question(id) ON DELETE CASCADE
);

CREATE TABLE quiz_attempt (
    id BIGSERIAL NOT NULL,
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    final_score DECIMAL(6,2),
    is_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    adaptive_plan JSONB,
    student_id BIGINT NOT NULL,
    quiz_id BIGINT NOT NULL,
    CONSTRAINT pk_quiz_attempt PRIMARY KEY (id),
    CONSTRAINT fk_quiz_attempt_student FOREIGN KEY (student_id) REFERENCES lms_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_quiz_attempt_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(id) ON DELETE CASCADE
);

CREATE TABLE attempt_answer (
    id BIGSERIAL NOT NULL,
    attempt_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    selected_choice_id BIGINT NOT NULL,
    CONSTRAINT pk_attempt_answer PRIMARY KEY (id),
    CONSTRAINT fk_attempt_answer_attempt FOREIGN KEY (attempt_id) REFERENCES quiz_attempt(id) ON DELETE CASCADE,
    CONSTRAINT fk_attempt_answer_question FOREIGN KEY (question_id) REFERENCES question(id) ON DELETE CASCADE,
    CONSTRAINT fk_attempt_answer_choice FOREIGN KEY (selected_choice_id) REFERENCES answer_choice(id) ON DELETE CASCADE,
    CONSTRAINT uk_attempt_answer_attempt_question UNIQUE (attempt_id, question_id)
);

CREATE TABLE proctoring_log (
    id BIGSERIAL NOT NULL,
    event_type VARCHAR(25) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    severity_score DECIMAL(4,2) NOT NULL DEFAULT 1.00,
    attempt_id BIGINT NOT NULL,
    CONSTRAINT pk_proctoring_log PRIMARY KEY (id),
    CONSTRAINT fk_proctoring_log_attempt FOREIGN KEY (attempt_id) REFERENCES quiz_attempt(id) ON DELETE CASCADE
);

-- ==========================================
-- APP: learning (Evaluations & Results)
-- ==========================================

CREATE TABLE evaluation (
    id BIGSERIAL NOT NULL,
    score DECIMAL(6,2) NOT NULL,
    max_score DECIMAL(6,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    student_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL,
    CONSTRAINT pk_evaluation PRIMARY KEY (id),
    CONSTRAINT fk_evaluation_student FOREIGN KEY (student_id) REFERENCES lms_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_evaluation_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
);

CREATE TABLE failed_topic (
    id BIGSERIAL NOT NULL,
    concept_id VARCHAR(100) NOT NULL,
    score DECIMAL(6,2) NOT NULL,
    max_score DECIMAL(6,2) NOT NULL,
    evaluation_id BIGINT NOT NULL,
    CONSTRAINT pk_failed_topic PRIMARY KEY (id),
    CONSTRAINT fk_failed_topic_evaluation FOREIGN KEY (evaluation_id) REFERENCES evaluation(id) ON DELETE CASCADE
);

CREATE TABLE evaluation_telemetry (
    id BIGSERIAL NOT NULL,
    time_on_task_seconds INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    evaluation_id BIGINT NOT NULL,
    CONSTRAINT pk_evaluation_telemetry PRIMARY KEY (id),
    CONSTRAINT fk_evaluation_telemetry_evaluation FOREIGN KEY (evaluation_id) REFERENCES evaluation(id) ON DELETE CASCADE,
    CONSTRAINT uk_evaluation_telemetry_evaluation UNIQUE (evaluation_id)
);

CREATE TABLE certificate (
    id BIGSERIAL NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    certificate_hash VARCHAR(64) NOT NULL DEFAULT '',
    student_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL,
    CONSTRAINT pk_certificate PRIMARY KEY (id),
    CONSTRAINT fk_certificate_student FOREIGN KEY (student_id) REFERENCES lms_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_certificate_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
    CONSTRAINT uk_certificate_student_course UNIQUE (student_id, course_id),
    CONSTRAINT uk_certificate_hash UNIQUE (certificate_hash)
);

-- ==========================================
-- INDEXES FOR FREQUENTLY QUERIED FKS
-- ==========================================
CREATE INDEX idx_semester_career ON semester(career_id);
CREATE INDEX idx_course_semester ON course(semester_id);
CREATE INDEX idx_module_course ON module(course_id);
CREATE INDEX idx_lesson_module ON lesson(module_id);
CREATE INDEX idx_resource_lesson ON resource(lesson_id);
CREATE INDEX idx_assignment_lesson ON assignment(lesson_id);
CREATE INDEX idx_submission_assignment ON submission(assignment_id);
CREATE INDEX idx_submission_student ON submission(student_id);
CREATE INDEX idx_quiz_course ON quiz(course_id);
CREATE INDEX idx_question_quiz ON question(quiz_id);
CREATE INDEX idx_answer_choice_question ON answer_choice(question_id);
CREATE INDEX idx_quiz_attempt_student ON quiz_attempt(student_id);
CREATE INDEX idx_quiz_attempt_quiz ON quiz_attempt(quiz_id);
CREATE INDEX idx_attempt_answer_attempt ON attempt_answer(attempt_id);
CREATE INDEX idx_proctoring_log_attempt ON proctoring_log(attempt_id);
CREATE INDEX idx_evaluation_student ON evaluation(student_id);
CREATE INDEX idx_evaluation_course ON evaluation(course_id);
CREATE INDEX idx_failed_topic_evaluation ON failed_topic(evaluation_id);
CREATE INDEX idx_certificate_student ON certificate(student_id);
CREATE INDEX idx_certificate_course ON certificate(course_id);
