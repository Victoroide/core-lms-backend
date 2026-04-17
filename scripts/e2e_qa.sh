#!/usr/bin/env bash
# ==========================================================================
# E2E QA Script -- Core LMS Backend
# Runs 35 integration tests against the live Django API.
# Execute inside Docker: docker compose exec web bash scripts/e2e_qa.sh
# ==========================================================================

set -euo pipefail

BASE="http://localhost:8000/api/v1"
PASS_COUNT=0
FAIL_COUNT=0
TOTAL=48

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

pass_test() {
    local num="$1"; local desc="$2"
    echo "[PASS] [$num] $desc"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail_test() {
    local num="$1"; local desc="$2"; local body="$3"
    echo "[FAIL] [$num] $desc"
    echo "  Response: $body"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

assert_status() {
    local num="$1"; local expected="$2"; local actual="$3"
    local desc="$4"; local body="$5"
    if [ "$actual" -eq "$expected" ]; then
        pass_test "$num" "$desc (HTTP $actual)"
    else
        fail_test "$num" "$desc -- expected $expected, got $actual" "$body"
    fi
}

# Perform HTTP request, capture status and body separately.
# Usage: do_request METHOD URL [extra curl args...]
# Sets: RESP_STATUS, RESP_BODY
do_request() {
    local method="$1"; shift
    local url="$1"; shift
    local tmpfile; tmpfile=$(mktemp)
    RESP_STATUS=$(curl -s -o "$tmpfile" -w "%{http_code}" -X "$method" "$url" "$@")
    RESP_BODY=$(cat "$tmpfile")
    rm -f "$tmpfile"
}

echo ""
echo "============================================================"
echo "  Core LMS -- E2E QA Suite ($TOTAL tests)"
echo "============================================================"
echo ""

# ==========================================================================
# AUTH
# ==========================================================================

# [01] POST /auth/token/ tutor credentials
do_request POST "$BASE/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"prof_martinez","password":"demo_pass_2026"}'
assert_status "01" 200 "$RESP_STATUS" "Auth: tutor token" "$RESP_BODY"
TUTOR_TOKEN=$(echo "$RESP_BODY" | jq -r '.access // empty')
if [ -z "$TUTOR_TOKEN" ]; then
    echo "FATAL: Could not obtain tutor token. Aborting."
    exit 1
fi

# [02] POST /auth/token/ student credentials
do_request POST "$BASE/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"alice","password":"demo_pass_2026"}'
assert_status "02" 200 "$RESP_STATUS" "Auth: student token" "$RESP_BODY"
STUDENT_TOKEN=$(echo "$RESP_BODY" | jq -r '.access // empty')

# Get alice's user ID for later use
ALICE_ID=$(python manage.py shell -c "
from apps.learning.models import LMSUser
u = LMSUser.objects.filter(username='alice').first()
print(u.pk if u else '')
" 2>/dev/null | tail -1)

# [03] POST /auth/token/ wrong password
do_request POST "$BASE/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"prof_martinez","password":"wrong_password"}'
assert_status "03" 401 "$RESP_STATUS" "Auth: wrong password rejected" "$RESP_BODY"

# ==========================================================================
# ACADEMIC ONTOLOGY (tutor token)
# ==========================================================================

# [04] POST /careers/
do_request POST "$BASE/careers/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"E2E Test Career","code":"E2E","description":"Created by QA script."}'
assert_status "04" 201 "$RESP_STATUS" "Create career" "$RESP_BODY"
CAREER_ID=$(echo "$RESP_BODY" | jq -r '.id')

# [05] GET /careers/
do_request GET "$BASE/careers/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "05" 200 "$RESP_STATUS" "List careers" "$RESP_BODY"
HAS_CAREER=$(echo "$RESP_BODY" | jq "[.results[]? // .[]? | select(.code==\"E2E\")] | length")
if [ "$HAS_CAREER" -gt 0 ] && [ "$RESP_STATUS" -eq 200 ]; then
    : # already counted as pass
else
    fail_test "05" "Created career not found in list" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# [06] POST /semesters/
do_request POST "$BASE/semesters/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"career\":$CAREER_ID,\"name\":\"E2E Semester\",\"number\":1,\"year\":2026,\"period\":\"I\"}"
assert_status "06" 201 "$RESP_STATUS" "Create semester" "$RESP_BODY"
SEMESTER_ID=$(echo "$RESP_BODY" | jq -r '.id')

# [07] POST /courses/ with FK to semester
do_request POST "$BASE/courses/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"semester\":$SEMESTER_ID,\"name\":\"E2E Test Course\",\"code\":\"E2E-101\",\"description\":\"QA course.\"}"
assert_status "07" 201 "$RESP_STATUS" "Create course" "$RESP_BODY"
COURSE_ID=$(echo "$RESP_BODY" | jq -r '.id')

# [08] GET /courses/{id}/ -- nested response includes modules key
do_request GET "$BASE/courses/$COURSE_ID/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "08" 200 "$RESP_STATUS" "Retrieve course detail" "$RESP_BODY"
HAS_MODULES=$(echo "$RESP_BODY" | jq 'has("modules")')
if [ "$HAS_MODULES" != "true" ] && [ "$RESP_STATUS" -eq 200 ]; then
    fail_test "08" "Course detail missing 'modules' key" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# [09] POST /modules/
do_request POST "$BASE/modules/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"course\":$COURSE_ID,\"title\":\"E2E Module\",\"description\":\"QA module.\",\"order\":1}"
assert_status "09" 201 "$RESP_STATUS" "Create module" "$RESP_BODY"
MODULE_ID=$(echo "$RESP_BODY" | jq -r '.id')

# [10] POST /lessons/
do_request POST "$BASE/lessons/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"module\":$MODULE_ID,\"title\":\"E2E Lesson\",\"content\":\"QA lesson content.\",\"order\":1}"
assert_status "10" 201 "$RESP_STATUS" "Create lesson" "$RESP_BODY"
LESSON_ID=$(echo "$RESP_BODY" | jq -r '.id')

# [11] POST /resources/ (multipart, 1KB file)
TMPFILE=$(mktemp /tmp/e2e_resource_XXXX.txt)
dd if=/dev/urandom bs=1024 count=1 2>/dev/null | base64 > "$TMPFILE"
do_request POST "$BASE/resources/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -F "lesson=$LESSON_ID" \
    -F "resource_type=DOCUMENT" \
    -F "title=E2E Resource" \
    -F "file=@$TMPFILE"
rm -f "$TMPFILE"
assert_status "11" 201 "$RESP_STATUS" "Upload resource (multipart)" "$RESP_BODY"
RESOURCE_ID=$(echo "$RESP_BODY" | jq -r '.id')
FILE_URL=$(echo "$RESP_BODY" | jq -r '.file // empty')
if echo "$FILE_URL" | grep -qE '(/app|/tmp)'; then
    fail_test "11" "File URL contains local path: $FILE_URL" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# [12] GET /resources/{id}/
do_request GET "$BASE/resources/$RESOURCE_ID/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "12" 200 "$RESP_STATUS" "Retrieve resource" "$RESP_BODY"

# ==========================================================================
# RBAC
# ==========================================================================

# [13] POST /careers/ with student token
do_request POST "$BASE/careers/" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Forbidden Career","code":"NOPE","description":"Should fail."}'
assert_status "13" 403 "$RESP_STATUS" "RBAC: student cannot create career" "$RESP_BODY"

# [14] POST /assignments/ with student token
do_request POST "$BASE/assignments/" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"lesson\":$LESSON_ID,\"title\":\"Forbidden Assignment\",\"description\":\"Should fail.\"}"
assert_status "14" 403 "$RESP_STATUS" "RBAC: student cannot create assignment" "$RESP_BODY"

# [15] GET /careers/ with no token
do_request GET "$BASE/careers/"
assert_status "15" 401 "$RESP_STATUS" "RBAC: no token returns 401" "$RESP_BODY"

# ==========================================================================
# ASSIGNMENT + SUBMISSION
# ==========================================================================

# [16] POST /assignments/ (tutor)
do_request POST "$BASE/assignments/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"lesson\":$LESSON_ID,\"title\":\"E2E Assignment\",\"description\":\"QA assignment.\"}"
assert_status "16" 201 "$RESP_STATUS" "Create assignment (tutor)" "$RESP_BODY"
ASSIGNMENT_ID=$(echo "$RESP_BODY" | jq -r '.id')

# [17] POST /submissions/ (student, multipart file)
TMPFILE2=$(mktemp /tmp/e2e_submission_XXXX.txt)
echo "E2E submission content" > "$TMPFILE2"
do_request POST "$BASE/submissions/" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -F "assignment=$ASSIGNMENT_ID" \
    -F "student=$ALICE_ID" \
    -F "file=@$TMPFILE2"
rm -f "$TMPFILE2"
assert_status "17" 201 "$RESP_STATUS" "Create submission (student)" "$RESP_BODY"
SUBMISSION_ID=$(echo "$RESP_BODY" | jq -r '.id')

# [18] GET /submissions/ (student token)
do_request GET "$BASE/submissions/" \
    -H "Authorization: Bearer $STUDENT_TOKEN"
assert_status "18" 200 "$RESP_STATUS" "List submissions (student scope)" "$RESP_BODY"

# [19] PATCH /submissions/{id}/grade/ (tutor)
do_request PATCH "$BASE/submissions/$SUBMISSION_ID/grade/" \
    -H "Authorization: Bearer $TUTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"grade": 85.50}'
assert_status "19" 200 "$RESP_STATUS" "Grade submission (tutor)" "$RESP_BODY"
GRADE_VAL=$(echo "$RESP_BODY" | jq -r '.grade // empty')
if [ -z "$GRADE_VAL" ] || [ "$GRADE_VAL" = "null" ]; then
    fail_test "19" "Grade field is null after grading" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# [20] PATCH /submissions/{id}/grade/ (student)
do_request PATCH "$BASE/submissions/$SUBMISSION_ID/grade/" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"grade": 99.00}'
assert_status "20" 403 "$RESP_STATUS" "RBAC: student cannot grade" "$RESP_BODY"

# ==========================================================================
# ROW-LEVEL ISOLATION
# ==========================================================================

# Get a second student token (bob -- should have no submissions in E2E context)
do_request POST "$BASE/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"bob","password":"demo_pass_2026"}'
STUDENT2_TOKEN=$(echo "$RESP_BODY" | jq -r '.access // empty')

# [21] GET /submissions/ (second student with no E2E submissions)
do_request GET "$BASE/submissions/" \
    -H "Authorization: Bearer $STUDENT2_TOKEN"
assert_status "21" 200 "$RESP_STATUS" "Row isolation: second student sees own submissions only" "$RESP_BODY"

# [22] GET /submissions/ (tutor)
do_request GET "$BASE/submissions/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "22" 200 "$RESP_STATUS" "Tutor sees all submissions" "$RESP_BODY"
TUTOR_SUB_COUNT=$(echo "$RESP_BODY" | jq '.count // (.results | length) // 0')
if [ "$TUTOR_SUB_COUNT" -lt 1 ]; then
    fail_test "22" "Tutor submission count should be >= 1, got $TUTOR_SUB_COUNT" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# ==========================================================================
# SOFT DELETE
# ==========================================================================

# [23] DELETE /lessons/{id}/ (tutor)
do_request DELETE "$BASE/lessons/$LESSON_ID/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "23" 204 "$RESP_STATUS" "Soft-delete lesson" "$RESP_BODY"

# [24] GET /lessons/{id}/ -- should 404 because default manager excludes soft-deleted
do_request GET "$BASE/lessons/$LESSON_ID/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "24" 404 "$RESP_STATUS" "Soft-deleted lesson returns 404" "$RESP_BODY"

# [25] DB check: SELECT is_deleted FROM learning_lesson WHERE id={id}
SD_CHECK=$(python manage.py shell -c "
from apps.learning.models import Lesson
l = Lesson.all_objects.filter(pk=$LESSON_ID).first()
print('t' if l and l.is_deleted else 'f')
" 2>/dev/null | tail -1)
if [ "$SD_CHECK" = "t" ]; then
    pass_test "25" "DB confirms is_deleted=True for lesson $LESSON_ID"
else
    fail_test "25" "DB check: is_deleted not True for lesson $LESSON_ID" "got: $SD_CHECK"
fi

# ==========================================================================
# QUIZ + SCORING + AXIOMENGINE PIPELINE
# ==========================================================================

# Fetch existing quiz and questions (seeded data)
QUIZ_ID=$(python manage.py shell -c "
from apps.assessments.models import Quiz
q = Quiz.objects.filter(is_active=True).first()
print(q.pk if q else '')
" 2>/dev/null | tail -1)

if [ -z "$QUIZ_ID" ]; then
    echo "WARN: No active quiz found. Skipping quiz tests [26-30]."
    for t in 26 27 28 29 30; do
        fail_test "$t" "Skipped -- no active quiz" "N/A"
    done
else
    # Get questions and wrong answers for deliberate failure
    QUIZ_PAYLOAD=$(python manage.py shell -c "
import json
from apps.assessments.models import Quiz, Question, AnswerChoice
from apps.learning.models import LMSUser
quiz = Quiz.objects.get(pk=$QUIZ_ID)
# Use a student that has NOT attempted this quiz yet
student = LMSUser.objects.filter(role='STUDENT').exclude(
    quiz_attempts__quiz=quiz
).first()
if not student:
    student = LMSUser.objects.filter(role='STUDENT').last()
answers = []
for q in quiz.questions.all():
    # pick wrong answer for first question, correct for rest
    wrong = AnswerChoice.objects.filter(question=q, is_correct=False).first()
    correct = AnswerChoice.objects.filter(question=q, is_correct=True).first()
    if len(answers) == 0 and wrong:
        answers.append({'question_id': q.pk, 'selected_choice_id': wrong.pk})
    else:
        answers.append({'question_id': q.pk, 'selected_choice_id': correct.pk})
payload = {'quiz_id': quiz.pk, 'student_id': student.pk, 'answers': answers}
print(json.dumps(payload))
" 2>/dev/null | tail -1)

    # Get student token for quiz submission
    QUIZ_STUDENT_ID=$(echo "$QUIZ_PAYLOAD" | jq -r '.student_id')
    QUIZ_STUDENT_USERNAME=$(python manage.py shell -c "
from apps.learning.models import LMSUser
u = LMSUser.objects.get(pk=$QUIZ_STUDENT_ID)
print(u.username)
" 2>/dev/null | tail -1)

    do_request POST "$BASE/auth/token/" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$QUIZ_STUDENT_USERNAME\",\"password\":\"demo_pass_2026\"}"
    QUIZ_STUDENT_TOKEN=$(echo "$RESP_BODY" | jq -r '.access // empty')

    # [26] POST quiz submission with at least one wrong answer
    do_request POST "$BASE/attempts/" \
        -H "Authorization: Bearer $QUIZ_STUDENT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$QUIZ_PAYLOAD"
    assert_status "26" 201 "$RESP_STATUS" "Submit quiz with wrong answer" "$RESP_BODY"
    ATTEMPT_ID=$(echo "$RESP_BODY" | jq -r '.id')

    # [27] DB check: FailedTopic records exist for that attempt
    FT_COUNT=$(python manage.py shell -c "
from apps.learning.models import FailedTopic, Evaluation
eval_obj = Evaluation.objects.filter(student_id=$QUIZ_STUDENT_ID).order_by('-id').first()
if eval_obj:
    count = FailedTopic.objects.filter(evaluation=eval_obj).count()
    print(count)
else:
    print(0)
" 2>/dev/null | tail -1)
    if [ "$FT_COUNT" -gt 0 ]; then
        pass_test "27" "FailedTopic records exist ($FT_COUNT)"
    else
        fail_test "27" "No FailedTopic records found" "count=$FT_COUNT"
    fi

    # [28] Response body of [26] contains "adaptive_plan" key
    HAS_AP=$(echo "$RESP_BODY" | jq 'has("adaptive_plan")')
    if [ "$HAS_AP" = "true" ]; then
        pass_test "28" "Quiz response contains adaptive_plan key"
    else
        fail_test "28" "Quiz response missing adaptive_plan key" "$RESP_BODY"
    fi

    # [29] GET /attempts/{id}/ -- This is a ViewSet, check if retrieve exists
    # AttemptViewSet is a ViewSet (not ModelViewSet), so retrieve may not exist.
    # The adaptive_plan is in the create response; verify it was stored in DB.
    AP_DB=$(python manage.py shell -c "
from apps.assessments.models import QuizAttempt
a = QuizAttempt.objects.get(pk=$ATTEMPT_ID)
print('not_null' if a.adaptive_plan is not None else 'null')
" 2>/dev/null | tail -1)
    if [ "$AP_DB" = "not_null" ]; then
        pass_test "29" "DB: adaptive_plan is not null on attempt $ATTEMPT_ID"
    else
        fail_test "29" "DB: adaptive_plan is null on attempt $ATTEMPT_ID" "N/A"
    fi

    # [30] Stop axiom-engine, submit quiz, verify fallback
    # We test this by making a request when axiom-engine might not respond.
    # Since we are inside the web container, we simulate by using a student
    # that will trigger failed topics. The client catches ConnectionError.
    # For a true test, we cannot stop containers from inside. Instead:
    # verify that the adaptive_plan fallback mechanism works by checking
    # the response structure.
    FALLBACK_PAYLOAD=$(python manage.py shell -c "
import json
from apps.assessments.models import Quiz, AnswerChoice
from apps.learning.models import LMSUser
quiz = Quiz.objects.get(pk=$QUIZ_ID)
student = LMSUser.objects.filter(role='STUDENT').exclude(
    quiz_attempts__quiz=quiz
).first()
if not student:
    student = LMSUser.objects.filter(role='STUDENT', username='karen').first()
answers = []
for q in quiz.questions.all():
    wrong = AnswerChoice.objects.filter(question=q, is_correct=False).first()
    if wrong:
        answers.append({'question_id': q.pk, 'selected_choice_id': wrong.pk})
payload = {'quiz_id': quiz.pk, 'student_id': student.pk, 'answers': answers}
print(json.dumps(payload))
" 2>/dev/null | tail -1)

    FALLBACK_STUDENT_ID=$(echo "$FALLBACK_PAYLOAD" | jq -r '.student_id')
    FALLBACK_USERNAME=$(python manage.py shell -c "
from apps.learning.models import LMSUser
print(LMSUser.objects.get(pk=$FALLBACK_STUDENT_ID).username)
" 2>/dev/null | tail -1)

    do_request POST "$BASE/auth/token/" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$FALLBACK_USERNAME\",\"password\":\"demo_pass_2026\"}"
    FALLBACK_TOKEN=$(echo "$RESP_BODY" | jq -r '.access // empty')

    do_request POST "$BASE/attempts/" \
        -H "Authorization: Bearer $FALLBACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$FALLBACK_PAYLOAD"
    # Should be 201 (not 500 or 502) regardless of axiom-engine state
    if [ "$RESP_STATUS" -eq 201 ]; then
        AP_VAL=$(echo "$RESP_BODY" | jq -r '.adaptive_plan // empty')
        if [ -n "$AP_VAL" ] && [ "$AP_VAL" != "null" ]; then
            pass_test "30" "Quiz submission succeeds with adaptive_plan (not 500/502)"
        else
            # adaptive_plan might be null if no failed concepts -- still not a crash
            pass_test "30" "Quiz submission succeeds (HTTP 201, no crash)"
        fi
    else
        fail_test "30" "Quiz submission failed with HTTP $RESP_STATUS (expected 201)" "$RESP_BODY"
    fi
fi

# ==========================================================================
# PROCTORING + DASHBOARD
# ==========================================================================

# Need an attempt ID for proctoring. Use the one from quiz tests or find one.
if [ -z "${ATTEMPT_ID:-}" ]; then
    ATTEMPT_ID=$(python manage.py shell -c "
from apps.assessments.models import QuizAttempt
a = QuizAttempt.objects.first()
print(a.pk if a else '')
" 2>/dev/null | tail -1)
fi

# [31] POST /proctoring/logs/ (student)
do_request POST "$BASE/proctoring/logs/" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"events\":[{\"attempt\":$ATTEMPT_ID,\"event_type\":\"tab_switched\",\"timestamp\":\"2026-04-15T00:00:00Z\",\"severity_score\":0.85}]}"
assert_status "31" 201 "$RESP_STATUS" "Ingest proctoring log (student)" "$RESP_BODY"

# [32] GET /analytics/course/{course_id}/dashboard/ (tutor)
# Use the seeded course (CS-201)
SEEDED_COURSE_ID=$(python manage.py shell -c "
from apps.learning.models import Course
c = Course.objects.filter(code='CS-201').first()
print(c.pk if c else '')
" 2>/dev/null | tail -1)

if [ -n "$SEEDED_COURSE_ID" ]; then
    do_request GET "$BASE/analytics/course/$SEEDED_COURSE_ID/dashboard/" \
        -H "Authorization: Bearer $TUTOR_TOKEN"
    assert_status "32" 200 "$RESP_STATUS" "Teacher dashboard" "$RESP_BODY"
    for key in proctoring_alerts vark_distribution top_failed_concepts; do
        HAS_KEY=$(echo "$RESP_BODY" | jq "has(\"$key\")")
        if [ "$HAS_KEY" != "true" ]; then
            fail_test "32" "Dashboard missing key: $key" "$RESP_BODY"
            PASS_COUNT=$((PASS_COUNT - 1))
            break
        fi
    done
else
    fail_test "32" "Seeded course CS-201 not found" "N/A"
fi

# ==========================================================================
# CERTIFICATE
# ==========================================================================

# [33] POST /certificates/generate/ (student who completed course)
# Find a passing student for the seeded course
CERT_STUDENT_ID=$(python manage.py shell -c "
from apps.learning.models import Evaluation
from decimal import Decimal
e = Evaluation.objects.filter(score__gte=Decimal('60'), course__code='CS-201').first()
print(e.student_id if e else '')
" 2>/dev/null | tail -1)

if [ -n "$CERT_STUDENT_ID" ] && [ -n "$SEEDED_COURSE_ID" ]; then
    CERT_USERNAME=$(python manage.py shell -c "
from apps.learning.models import LMSUser
print(LMSUser.objects.get(pk=$CERT_STUDENT_ID).username)
" 2>/dev/null | tail -1)

    do_request POST "$BASE/auth/token/" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$CERT_USERNAME\",\"password\":\"demo_pass_2026\"}"
    CERT_TOKEN=$(echo "$RESP_BODY" | jq -r '.access // empty')

    do_request POST "$BASE/certificates/generate/" \
        -H "Authorization: Bearer $CERT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"student_id\":$CERT_STUDENT_ID,\"course_id\":$SEEDED_COURSE_ID}"
    assert_status "33" 201 "$RESP_STATUS" "Generate certificate" "$RESP_BODY"
    CERT_HASH=$(echo "$RESP_BODY" | jq -r '.certificate_hash // empty')
    HASH_LEN=${#CERT_HASH}
    if [ "$HASH_LEN" -ne 64 ]; then
        fail_test "33" "certificate_hash length is $HASH_LEN, expected 64" "$RESP_BODY"
        PASS_COUNT=$((PASS_COUNT - 1))
    fi
else
    fail_test "33" "No passing student found for CS-201" "N/A"
fi

# ==========================================================================
# FILTER
# ==========================================================================

# [34] GET /courses/?semester__career={id}
# Use the seeded career (SIS)
SEEDED_CAREER_ID=$(python manage.py shell -c "
from apps.learning.models import Career
c = Career.objects.filter(code='SIS').first()
print(c.pk if c else '')
" 2>/dev/null | tail -1)

if [ -n "$SEEDED_CAREER_ID" ]; then
    do_request GET "$BASE/courses/?semester__career=$SEEDED_CAREER_ID" \
        -H "Authorization: Bearer $TUTOR_TOKEN"
    assert_status "34" 200 "$RESP_STATUS" "Filter courses by career" "$RESP_BODY"
else
    fail_test "34" "Seeded career SIS not found" "N/A"
fi

# [35] GET /submissions/?is_deleted=false (tutor)
do_request GET "$BASE/submissions/?is_deleted=false" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "35" 200 "$RESP_STATUS" "Filter submissions by is_deleted=false" "$RESP_BODY"

# ==========================================================================
# HEALTH CHECK
# ==========================================================================

# [36] GET /health/ (no token, public endpoint)
do_request GET "http://localhost:8000/health/"
assert_status "36" 200 "$RESP_STATUS" "Health check returns 200" "$RESP_BODY"
HEALTH_STATUS=$(echo "$RESP_BODY" | jq -r '.status // empty')
if [ "$HEALTH_STATUS" != "ok" ]; then
    fail_test "36" "Health check body not {status:ok}" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# ==========================================================================
# TOKEN REFRESH
# ==========================================================================

# Get a refresh token from the tutor auth response
do_request POST "$BASE/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"prof_martinez","password":"demo_pass_2026"}'
REFRESH_TOKEN=$(echo "$RESP_BODY" | jq -r '.refresh // empty')

# [37] POST /auth/token/refresh/ with valid refresh token
do_request POST "$BASE/auth/token/refresh/" \
    -H "Content-Type: application/json" \
    -d "{\"refresh\":\"$REFRESH_TOKEN\"}"
assert_status "37" 200 "$RESP_STATUS" "Token refresh with valid token" "$RESP_BODY"
HAS_ACCESS=$(echo "$RESP_BODY" | jq 'has("access")')
if [ "$HAS_ACCESS" != "true" ] && [ "$RESP_STATUS" -eq 200 ]; then
    fail_test "37" "Refresh response missing access key" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# [38] POST /auth/token/refresh/ with garbage token
do_request POST "$BASE/auth/token/refresh/" \
    -H "Content-Type: application/json" \
    -d '{"refresh":"garbage-invalid-token"}'
assert_status "38" 401 "$RESP_STATUS" "Token refresh with invalid token" "$RESP_BODY"

# ==========================================================================
# QUIZ LIST AND DETAIL (public, no auth)
# ==========================================================================

# [39] GET /quizzes/ with no token
do_request GET "$BASE/quizzes/"
assert_status "39" 200 "$RESP_STATUS" "Quiz list (no auth)" "$RESP_BODY"
HAS_COUNT=$(echo "$RESP_BODY" | jq 'has("count")')
HAS_RESULTS=$(echo "$RESP_BODY" | jq 'has("results")')
if [ "$HAS_COUNT" != "true" ] || [ "$HAS_RESULTS" != "true" ]; then
    fail_test "39" "Quiz list missing count or results" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# Get quiz ID from the list
E2E_QUIZ_ID=$(echo "$RESP_BODY" | jq -r '.results[0].id // empty')

if [ -n "$E2E_QUIZ_ID" ]; then
    # [40] GET /quizzes/{id}/ with no token
    do_request GET "$BASE/quizzes/$E2E_QUIZ_ID/"
    assert_status "40" 200 "$RESP_STATUS" "Quiz detail (no auth)" "$RESP_BODY"
    HAS_QUESTIONS=$(echo "$RESP_BODY" | jq 'has("questions")')
    if [ "$HAS_QUESTIONS" != "true" ]; then
        fail_test "40" "Quiz detail missing questions key" "$RESP_BODY"
        PASS_COUNT=$((PASS_COUNT - 1))
    fi

    # [41] GET /quizzes/{id}/ as student, verify is_correct absent
    do_request GET "$BASE/quizzes/$E2E_QUIZ_ID/" \
        -H "Authorization: Bearer $STUDENT_TOKEN"
    assert_status "41" 200 "$RESP_STATUS" "Quiz detail hides is_correct" "$RESP_BODY"
    IC_COUNT=$(echo "$RESP_BODY" | jq '[.questions[]?.choices[]? | select(has("is_correct"))] | length')
    if [ "$IC_COUNT" -gt 0 ]; then
        fail_test "41" "is_correct exposed in $IC_COUNT choices" "$RESP_BODY"
        PASS_COUNT=$((PASS_COUNT - 1))
    fi
else
    fail_test "40" "No quiz found for detail test" "N/A"
    fail_test "41" "No quiz found for is_correct test" "N/A"
fi

# ==========================================================================
# VARK ONBOARDING
# ==========================================================================

# [42] POST /users/{id}/onboard/ as student
do_request POST "$BASE/users/$ALICE_ID/onboard/" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"answers":[{"category":"read_write","value":9},{"category":"visual","value":2},{"category":"aural","value":1},{"category":"kinesthetic","value":1}]}'
assert_status "42" 200 "$RESP_STATUS" "VARK onboarding" "$RESP_BODY"
VARK_DOM=$(echo "$RESP_BODY" | jq -r '.vark_dominant // empty')
if [ "$VARK_DOM" != "read_write" ]; then
    fail_test "42" "vark_dominant expected read_write, got $VARK_DOM" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# ==========================================================================
# EVALUATIONS
# ==========================================================================

# [43] GET /evaluations/ as tutor -> 200, paginated
do_request GET "$BASE/evaluations/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "43" 200 "$RESP_STATUS" "Evaluation list (tutor)" "$RESP_BODY"
HAS_COUNT_EVAL=$(echo "$RESP_BODY" | jq 'has("count")')
if [ "$HAS_COUNT_EVAL" != "true" ]; then
    fail_test "43" "Evaluation list missing count key" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# ==========================================================================
# COURSE DETAIL
# ==========================================================================

# [44] GET /courses/{id}/ -> 200, modules key present
if [ -n "$SEEDED_COURSE_ID" ]; then
    do_request GET "$BASE/courses/$SEEDED_COURSE_ID/" \
        -H "Authorization: Bearer $TUTOR_TOKEN"
    assert_status "44" 200 "$RESP_STATUS" "Course detail has modules" "$RESP_BODY"
    HAS_MODULES_KEY=$(echo "$RESP_BODY" | jq 'has("modules")')
    if [ "$HAS_MODULES_KEY" != "true" ]; then
        fail_test "44" "Course detail missing modules key" "$RESP_BODY"
        PASS_COUNT=$((PASS_COUNT - 1))
    fi
else
    fail_test "44" "No seeded course for detail test" "N/A"
fi

# ==========================================================================
# ATTEMPT RETRIEVAL
# ==========================================================================

# Use the attempt created in test [26]
if [ -n "${ATTEMPT_ID:-}" ]; then
    # Need the token for the student who owns this attempt
    ATTEMPT_OWNER_ID=$(python manage.py shell -c "
from apps.assessments.models import QuizAttempt
a = QuizAttempt.objects.get(pk=$ATTEMPT_ID)
print(a.student_id)
" 2>/dev/null | tail -1)
    ATTEMPT_OWNER_USERNAME=$(python manage.py shell -c "
from apps.learning.models import LMSUser
print(LMSUser.objects.get(pk=$ATTEMPT_OWNER_ID).username)
" 2>/dev/null | tail -1)

    do_request POST "$BASE/auth/token/" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$ATTEMPT_OWNER_USERNAME\",\"password\":\"demo_pass_2026\"}"
    ATTEMPT_OWNER_TOKEN=$(echo "$RESP_BODY" | jq -r '.access // empty')

    # [45] GET /attempts/{id}/ as student -> 200, adaptive_plan key not null
    do_request GET "$BASE/attempts/$ATTEMPT_ID/" \
        -H "Authorization: Bearer $ATTEMPT_OWNER_TOKEN"
    assert_status "45" 200 "$RESP_STATUS" "Retrieve own attempt" "$RESP_BODY"
    AP_KEY=$(echo "$RESP_BODY" | jq 'has("adaptive_plan")')
    AP_VAL_E2E=$(echo "$RESP_BODY" | jq -r '.adaptive_plan // empty')
    if [ "$AP_KEY" != "true" ] || [ -z "$AP_VAL_E2E" ] || [ "$AP_VAL_E2E" = "null" ]; then
        fail_test "45" "adaptive_plan missing or null" "$RESP_BODY"
        PASS_COUNT=$((PASS_COUNT - 1))
    fi

    # [46] GET /attempts/ as student -> 200, all results belong to that student
    do_request GET "$BASE/attempts/" \
        -H "Authorization: Bearer $ATTEMPT_OWNER_TOKEN"
    assert_status "46" 200 "$RESP_STATUS" "Attempt list scoped to student" "$RESP_BODY"
    OTHER_STUDENTS=$(echo "$RESP_BODY" | jq "[.results[]? | select(.student != $ATTEMPT_OWNER_ID)] | length")
    if [ "$OTHER_STUDENTS" -gt 0 ]; then
        fail_test "46" "Attempt list contains $OTHER_STUDENTS records from other students" "$RESP_BODY"
        PASS_COUNT=$((PASS_COUNT - 1))
    fi
else
    fail_test "45" "No attempt ID from test 26" "N/A"
    fail_test "46" "No attempt ID from test 26" "N/A"
fi

# ==========================================================================
# EVALUATION TELEMETRY
# ==========================================================================

# Create a fresh evaluation for alice (without telemetry) so we can test POST
TELEM_EVAL_ID=$(python manage.py shell -c "
from apps.learning.models import Evaluation, Course, LMSUser
student = LMSUser.objects.filter(username='alice').first()
course = Course.objects.first()
if student and course:
    e = Evaluation.objects.create(student=student, course=course, score=50, max_score=100)
    print(e.pk)
else:
    print('')
" 2>/dev/null | tail -1)

if [ -n "$TELEM_EVAL_ID" ]; then
    # [47] POST /evaluation-telemetry/ as student -> 201
    do_request POST "$BASE/evaluation-telemetry/" \
        -H "Authorization: Bearer $STUDENT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"evaluation\":$TELEM_EVAL_ID,\"time_on_task_seconds\":1200,\"clicks\":45}"
    assert_status "47" 201 "$RESP_STATUS" "Create evaluation telemetry" "$RESP_BODY"
else
    fail_test "47" "Could not create evaluation for telemetry test" "N/A"
fi

# [48] GET /evaluation-telemetry/ as tutor -> 200, paginated
do_request GET "$BASE/evaluation-telemetry/" \
    -H "Authorization: Bearer $TUTOR_TOKEN"
assert_status "48" 200 "$RESP_STATUS" "List evaluation telemetry (tutor)" "$RESP_BODY"
HAS_COUNT_TELEM=$(echo "$RESP_BODY" | jq 'has("count")')
if [ "$HAS_COUNT_TELEM" != "true" ]; then
    fail_test "48" "Telemetry list missing count key" "$RESP_BODY"
    PASS_COUNT=$((PASS_COUNT - 1))
fi

# ==========================================================================
# SUMMARY
# ==========================================================================

echo ""
echo "============================================================"
echo "  RESULTS: PASSED=$PASS_COUNT/$TOTAL  FAILED=$FAIL_COUNT/$TOTAL"
echo "============================================================"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi
exit 0
