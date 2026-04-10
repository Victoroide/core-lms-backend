"""
Management command: seed_data
Populates the database with realistic demo data for a university defense
presentation. Designed for idempotency -- clears all existing non-superuser
data before seeding.

Usage:
    python manage.py seed_data
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from assessments.models import (
    AnswerChoice,
    AttemptAnswer,
    ProctoringLog,
    Question,
    Quiz,
    QuizAttempt,
)
from learning.models import (
    Certificate,
    Course,
    Evaluation,
    EvaluationTelemetry,
    FailedTopic,
    LMSUser,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VARK_CHOICES = [v[0] for v in LMSUser.VARKProfile.choices]

QUESTION_BANK = [
    {
        "concept_id": "Variables",
        "text": "Which statement correctly declares and initializes a variable in Python?",
        "choices": [
            {"text": "var x = 10", "is_correct": False},
            {"text": "x := 10", "is_correct": False},
            {"text": "x = 10", "is_correct": True},
            {"text": "int x = 10;", "is_correct": False},
        ],
    },
    {
        "concept_id": "Functions",
        "text": "What is the correct syntax to define a function in Python?",
        "choices": [
            {"text": "function my_func():", "is_correct": False},
            {"text": "def my_func():", "is_correct": True},
            {"text": "fun my_func():", "is_correct": False},
            {"text": "define my_func():", "is_correct": False},
        ],
    },
    {
        "concept_id": "Objects",
        "text": "In OOP, what is an object?",
        "choices": [
            {"text": "A blueprint for creating instances", "is_correct": False},
            {"text": "A module that contains functions", "is_correct": False},
            {"text": "An instance of a class that encapsulates state and behavior", "is_correct": True},
            {"text": "A global variable accessible from any scope", "is_correct": False},
        ],
    },
    {
        "concept_id": "Polymorphism",
        "text": "Which principle allows a single interface to represent different underlying data types?",
        "choices": [
            {"text": "Encapsulation", "is_correct": False},
            {"text": "Polymorphism", "is_correct": True},
            {"text": "Abstraction", "is_correct": False},
            {"text": "Composition", "is_correct": False},
        ],
    },
    {
        "concept_id": "Inheritance",
        "text": "What does inheritance enable in object-oriented programming?",
        "choices": [
            {"text": "Hiding internal implementation details", "is_correct": False},
            {"text": "Running multiple threads concurrently", "is_correct": False},
            {"text": "Deriving new classes from existing ones to reuse code", "is_correct": True},
            {"text": "Storing data in key-value pairs", "is_correct": False},
        ],
    },
]

STUDENT_NAMES = [
    ("alice", "Alice", "Johnson"),
    ("bob", "Bob", "Smith"),
    ("carla", "Carla", "Martinez"),
    ("diego", "Diego", "Rivera"),
    ("elena", "Elena", "Vasquez"),
    ("frank", "Frank", "Wilson"),
    ("grace", "Grace", "Kim"),
    ("henry", "Henry", "Chen"),
    ("isabella", "Isabella", "Thomas"),
    ("jack", "Jack", "Brown"),
    ("karen", "Karen", "Davis"),
    ("leo", "Leo", "Garcia"),
    ("maria", "Maria", "Lopez"),
    ("nathan", "Nathan", "Anderson"),
    ("olivia", "Olivia", "Taylor"),
    ("pablo", "Pablo", "Hernandez"),
    ("quinn", "Quinn", "Moore"),
    ("rachel", "Rachel", "White"),
    ("samuel", "Samuel", "Clark"),
]


class Command(BaseCommand):
    help = "Seed the database with realistic demo data for CS-201."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "--- Core LMS Data Seeder ---"
        ))
        self.stdout.write(self.style.WARNING(
            "Clearing existing data for idempotent re-seeding..."
        ))

        self._clear_data()
        course = self._create_course()
        teacher, students = self._create_users()
        quiz, questions, correct_map = self._create_quiz(course)
        self._create_attempts(students, quiz, questions, correct_map, course)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "=== Data seeding completed successfully ==="
        ))

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _clear_data(self):
        """Delete all seeded data in dependency-safe order."""
        counts = {}
        counts["Certificate"] = Certificate.objects.all().delete()[0]
        counts["ProctoringLog"] = ProctoringLog.objects.all().delete()[0]
        counts["AttemptAnswer"] = AttemptAnswer.objects.all().delete()[0]
        counts["QuizAttempt"] = QuizAttempt.objects.all().delete()[0]
        counts["AnswerChoice"] = AnswerChoice.objects.all().delete()[0]
        counts["Question"] = Question.objects.all().delete()[0]
        counts["Quiz"] = Quiz.objects.all().delete()[0]
        counts["EvaluationTelemetry"] = EvaluationTelemetry.objects.all().delete()[0]
        counts["FailedTopic"] = FailedTopic.objects.all().delete()[0]
        counts["Evaluation"] = Evaluation.objects.all().delete()[0]
        counts["LMSUser (non-superuser)"] = LMSUser.objects.filter(
            is_superuser=False
        ).delete()[0]
        counts["Course"] = Course.objects.all().delete()[0]

        for model_name, count in counts.items():
            if count > 0:
                self.stdout.write(f"  Deleted {count} {model_name} record(s).")

        self.stdout.write(self.style.SUCCESS("  Cleanup complete."))

    # ------------------------------------------------------------------
    # Course
    # ------------------------------------------------------------------

    def _create_course(self):
        course = Course.objects.create(
            name="Advanced Programming",
            code="CS-201",
            description=(
                "In-depth study of object-oriented design patterns, "
                "polymorphism, and advanced Python programming constructs."
            ),
        )
        self.stdout.write(self.style.SUCCESS(
            f"  Created Course: {course.code} -- {course.name}"
        ))
        return course

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _create_users(self):
        random.seed(42)

        teacher = LMSUser.objects.create_user(
            username="prof_martinez",
            first_name="Carlos",
            last_name="Martinez",
            email="c.martinez@university.edu",
            password="demo_pass_2026",
            role=LMSUser.Role.TUTOR,
            vark_dominant=LMSUser.VARKProfile.READ_WRITE,
        )
        self.stdout.write(self.style.SUCCESS(
            f"  Created Tutor: {teacher.username} ({teacher.first_name} {teacher.last_name})"
        ))

        students = []
        for username, first_name, last_name in STUDENT_NAMES:
            student = LMSUser.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=f"{username}@student.university.edu",
                password="demo_pass_2026",
                role=LMSUser.Role.STUDENT,
                vark_dominant=random.choice(VARK_CHOICES),
            )
            students.append(student)

        self.stdout.write(self.style.SUCCESS(
            f"  Created {len(students)} Students with randomized VARK profiles."
        ))
        return teacher, students

    # ------------------------------------------------------------------
    # Quiz & Questions
    # ------------------------------------------------------------------

    def _create_quiz(self, course):
        quiz = Quiz.objects.create(
            course=course,
            title="Midterm Exam",
            description="Comprehensive midterm covering core OOP and Python fundamentals.",
            time_limit_minutes=45,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f"  Created Quiz: \"{quiz.title}\" ({len(QUESTION_BANK)} questions)"
        ))

        questions = []
        correct_map = {}

        for order, q_data in enumerate(QUESTION_BANK, start=1):
            question = Question.objects.create(
                quiz=quiz,
                text=q_data["text"],
                concept_id=q_data["concept_id"],
                order=order,
            )
            questions.append(question)

            for choice_data in q_data["choices"]:
                choice = AnswerChoice.objects.create(
                    question=question,
                    text=choice_data["text"],
                    is_correct=choice_data["is_correct"],
                )
                if choice_data["is_correct"]:
                    correct_map[question.pk] = choice

        self.stdout.write(self.style.SUCCESS(
            f"  Created {sum(len(q['choices']) for q in QUESTION_BANK)} AnswerChoices "
            f"across {len(QUESTION_BANK)} Questions."
        ))
        concepts_str = ", ".join(q["concept_id"] for q in QUESTION_BANK)
        self.stdout.write(f"  Concept IDs: [{concepts_str}]")

        return quiz, questions, correct_map

    # ------------------------------------------------------------------
    # Quiz Attempts, Evaluations, FailedTopics, Proctoring
    # ------------------------------------------------------------------

    def _create_attempts(self, students, quiz, questions, correct_map, course):
        random.seed(42)
        now = timezone.now()
        attempt_students = students[:10]
        passing_students = attempt_students[:7]
        failing_students = attempt_students[7:10]
        proctoring_students = failing_students[:2]

        total_questions = len(questions)
        attempt_count = 0
        eval_count = 0
        failed_topic_count = 0
        proctoring_count = 0

        # --- Indices of "Objects" and "Polymorphism" questions ----------------
        objects_idx = next(
            i for i, q in enumerate(questions) if q.concept_id == "Objects"
        )
        poly_idx = next(
            i for i, q in enumerate(questions) if q.concept_id == "Polymorphism"
        )

        # --- Passing students (7) --------------------------------------------
        for student in passing_students:
            attempt_start = now - timedelta(
                hours=random.randint(24, 168)
            )
            attempt = QuizAttempt.objects.create(
                student=student,
                quiz=quiz,
                end_time=attempt_start + timedelta(minutes=random.randint(20, 44)),
                is_submitted=True,
            )
            # Force the auto_now_add start_time via update
            QuizAttempt.objects.filter(pk=attempt.pk).update(start_time=attempt_start)

            correct_count = 0
            for i, question in enumerate(questions):
                correct_choice = correct_map[question.pk]
                # Pass students get 4 or 5 correct -- randomly miss at most 1
                # but never miss Objects or Polymorphism (those are the key ones)
                pick_correct = True
                if i not in (objects_idx, poly_idx) and random.random() < 0.15:
                    pick_correct = False

                if pick_correct:
                    selected = correct_choice
                    correct_count += 1
                else:
                    wrong_choices = list(
                        AnswerChoice.objects.filter(
                            question=question, is_correct=False
                        )
                    )
                    selected = random.choice(wrong_choices)

                AttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_choice=selected,
                )

            score = Decimal(str(round(correct_count / total_questions * 100, 2)))
            QuizAttempt.objects.filter(pk=attempt.pk).update(final_score=score)

            # Evaluation record
            evaluation = Evaluation.objects.create(
                student=student,
                course=course,
                score=score,
                max_score=Decimal("100.00"),
            )
            EvaluationTelemetry.objects.create(
                evaluation=evaluation,
                time_on_task_seconds=random.randint(1200, 2640),
                clicks=random.randint(30, 120),
            )

            attempt_count += 1
            eval_count += 1

        # --- Failing students (3) -- fail Objects and Polymorphism -----------
        for student in failing_students:
            attempt_start = now - timedelta(hours=random.randint(24, 168))
            attempt = QuizAttempt.objects.create(
                student=student,
                quiz=quiz,
                end_time=attempt_start + timedelta(minutes=random.randint(10, 30)),
                is_submitted=True,
            )
            QuizAttempt.objects.filter(pk=attempt.pk).update(start_time=attempt_start)

            correct_count = 0
            failed_concepts = []

            for i, question in enumerate(questions):
                correct_choice = correct_map[question.pk]

                # Failing students always miss Objects and Polymorphism
                if i in (objects_idx, poly_idx):
                    wrong_choices = list(
                        AnswerChoice.objects.filter(
                            question=question, is_correct=False
                        )
                    )
                    selected = random.choice(wrong_choices)
                    failed_concepts.append(question.concept_id)
                # Also randomly miss some others -- end up with 1-2 correct max
                elif random.random() < 0.50:
                    wrong_choices = list(
                        AnswerChoice.objects.filter(
                            question=question, is_correct=False
                        )
                    )
                    selected = random.choice(wrong_choices)
                    failed_concepts.append(question.concept_id)
                else:
                    selected = correct_choice
                    correct_count += 1

                AttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_choice=selected,
                )

            score = Decimal(str(round(correct_count / total_questions * 100, 2)))
            QuizAttempt.objects.filter(pk=attempt.pk).update(final_score=score)

            evaluation = Evaluation.objects.create(
                student=student,
                course=course,
                score=score,
                max_score=Decimal("100.00"),
            )
            EvaluationTelemetry.objects.create(
                evaluation=evaluation,
                time_on_task_seconds=random.randint(600, 1200),
                clicks=random.randint(15, 50),
            )

            for concept_id in failed_concepts:
                FailedTopic.objects.create(
                    evaluation=evaluation,
                    concept_id=concept_id,
                    score=Decimal("0.00"),
                    max_score=Decimal("20.00"),
                )
                failed_topic_count += 1

            attempt_count += 1
            eval_count += 1

        # --- Proctoring logs for 2 suspicious students -----------------------
        for student in proctoring_students:
            attempt = QuizAttempt.objects.filter(
                student=student, quiz=quiz
            ).first()
            if not attempt:
                continue

            base_time = attempt.start_time or (now - timedelta(hours=48))

            # tab_switched events
            for offset_minutes in (3, 7, 14):
                ProctoringLog.objects.create(
                    attempt=attempt,
                    event_type=ProctoringLog.EventType.TAB_SWITCHED,
                    timestamp=base_time + timedelta(minutes=offset_minutes),
                    severity_score=Decimal("0.85"),
                )
                proctoring_count += 1

            # multiple_faces events
            for offset_minutes in (5, 18):
                ProctoringLog.objects.create(
                    attempt=attempt,
                    event_type=ProctoringLog.EventType.MULTIPLE_FACES,
                    timestamp=base_time + timedelta(minutes=offset_minutes),
                    severity_score=Decimal("0.95"),
                )
                proctoring_count += 1

        # --- Summary output ---------------------------------------------------
        self.stdout.write(self.style.SUCCESS(
            f"  Created {attempt_count} QuizAttempts "
            f"(7 passing, 3 failing)."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Created {eval_count} Evaluations with telemetry."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Created {failed_topic_count} FailedTopic records "
            f"(Objects, Polymorphism)."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Created {proctoring_count} ProctoringLog events "
            f"for {len(proctoring_students)} suspicious students."
        ))
