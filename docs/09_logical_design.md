# AxiomLMS Logical Design

**lms_user**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
  </tr>
  <tr>
    <td>id</td>
    <td>password</td>
    <td>last_login</td>
    <td>is_superuser</td>
    <td>username</td>
    <td>first_name</td>
    <td>last_name</td>
    <td>email</td>
    <td>is_staff</td>
    <td>is_active</td>
    <td>date_joined</td>
    <td>role</td>
    <td>vark_dominant</td>
  </tr>
</table>

**career**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>name</td>
    <td>code</td>
    <td>description</td>
    <td>created_at</td>
  </tr>
</table>

**semester**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>name</td>
    <td>number</td>
    <td>year</td>
    <td>period</td>
    <td>created_at</td>
    <td>career_id</td>
  </tr>
</table>

**course**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>name</td>
    <td>code</td>
    <td>description</td>
    <td>created_at</td>
    <td>semester_id</td>
  </tr>
</table>

**module**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>title</td>
    <td>description</td>
    <td>order</td>
    <td>course_id</td>
  </tr>
</table>

**lesson**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>title</td>
    <td>content</td>
    <td>order</td>
    <td>module_id</td>
  </tr>
</table>

**resource**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>file</td>
    <td>resource_type</td>
    <td>title</td>
    <td>created_at</td>
    <td>lesson_id</td>
    <td>uploaded_by_id</td>
  </tr>
</table>

**assignment**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>title</td>
    <td>description</td>
    <td>due_date</td>
    <td>max_score</td>
    <td>created_at</td>
    <td>lesson_id</td>
    <td>created_by_id</td>
  </tr>
</table>

**submission**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>is_deleted</td>
    <td>deleted_at</td>
    <td>file</td>
    <td>submitted_at</td>
    <td>grade</td>
    <td>graded_at</td>
    <td>assignment_id</td>
    <td>student_id</td>
  </tr>
</table>

**quiz**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>title</td>
    <td>description</td>
    <td>time_limit_minutes</td>
    <td>is_active</td>
    <td>created_at</td>
    <td>course_id</td>
  </tr>
</table>

**question**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>text</td>
    <td>concept_id</td>
    <td>order</td>
    <td>quiz_id</td>
  </tr>
</table>

**answer_choice**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>text</td>
    <td>is_correct</td>
    <td>question_id</td>
  </tr>
</table>

**quiz_attempt**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>start_time</td>
    <td>end_time</td>
    <td>final_score</td>
    <td>is_submitted</td>
    <td>adaptive_plan</td>
    <td>student_id</td>
    <td>quiz_id</td>
  </tr>
</table>

**attempt_answer**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>attempt_id</td>
    <td>question_id</td>
    <td>selected_choice_id</td>
  </tr>
</table>

**proctoring_log**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>event_type</td>
    <td>timestamp</td>
    <td>severity_score</td>
    <td>attempt_id</td>
  </tr>
</table>

**evaluation**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>score</td>
    <td>max_score</td>
    <td>created_at</td>
    <td>student_id</td>
    <td>course_id</td>
  </tr>
</table>

**failed_topic**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>concept_id</td>
    <td>score</td>
    <td>max_score</td>
    <td>evaluation_id</td>
  </tr>
</table>

**evaluation_telemetry**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>time_on_task_seconds</td>
    <td>clicks</td>
    <td>evaluation_id</td>
  </tr>
</table>

**certificate**

<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <td>PK</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td><em>FK</em></td>
    <td><em>FK</em></td>
  </tr>
  <tr>
    <td>id</td>
    <td>issued_at</td>
    <td>certificate_hash</td>
    <td>student_id</td>
    <td>course_id</td>
  </tr>
</table>
