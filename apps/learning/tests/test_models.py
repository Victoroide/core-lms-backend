"""Unit tests for learning app models, storage callables, and certificate hashing."""

import re
from decimal import Decimal
from unittest.mock import Mock

from django.test import TestCase

from apps.learning.models import Career, Course, Evaluation, LMSUser
from apps.learning.services import CertificateGenerator
from apps.learning.services.storage_service import resource_upload_path
from apps.curriculum.services.storage_service import submission_upload_path


class TestSoftDelete(TestCase):
    """Verify SoftDeleteMixin behavior on a concrete model (Career)."""

    def setUp(self):
        """Create a single Career record for soft-delete testing."""
        self.career = Career.objects.create(
            name="Test Career",
            code="TST",
            description="Soft-delete test career.",
        )
        self.career_pk = self.career.pk

    def test_soft_delete_sets_is_deleted_and_deleted_at(self):
        """delete() sets is_deleted=True and populates deleted_at without SQL DELETE."""
        self.career.delete()
        self.career.refresh_from_db()
        self.assertTrue(self.career.is_deleted)
        self.assertIsNotNone(self.career.deleted_at)

    def test_hard_delete_removes_record(self):
        """hard_delete() permanently removes the record from the database."""
        self.career.hard_delete()
        self.assertFalse(Career.all_objects.filter(pk=self.career_pk).exists())

    def test_soft_delete_manager_excludes_deleted(self):
        """SoftDeleteManager (.objects) excludes soft-deleted records."""
        self.career.delete()
        self.assertFalse(Career.objects.filter(pk=self.career_pk).exists())

    def test_all_objects_manager_includes_deleted(self):
        """AllObjectsManager (.all_objects) includes soft-deleted records."""
        self.career.delete()
        self.assertTrue(Career.all_objects.filter(pk=self.career_pk).exists())


class TestStorageCallables(TestCase):
    """Verify upload_to path functions produce correct S3 object keys."""

    def test_resource_upload_path(self):
        """resource_upload_path returns resources/{course_id}/{filename}."""
        instance = Mock()
        instance.lesson.module.course_id = 42
        result = resource_upload_path(instance, "notes.pdf")
        self.assertEqual(result, "resources/42/notes.pdf")

    def test_submission_upload_path(self):
        """submission_upload_path returns submissions/{student_id}/{filename}."""
        instance = Mock()
        instance.student_id = 7
        result = submission_upload_path(instance, "homework.docx")
        self.assertEqual(result, "submissions/7/homework.docx")


class TestCertificate(TestCase):
    """Verify certificate_hash is a valid SHA-256 hexadecimal string."""

    def setUp(self):
        """Create the prerequisite records for certificate issuance."""
        self.student = LMSUser.objects.create_user(
            username="cert_student",
            password="testpass123",
            role="STUDENT",
            vark_dominant="visual",
        )
        self.course = Course.objects.create(
            name="Cert Course",
            code="CERT-101",
            description="Course for certificate testing.",
        )
        Evaluation.objects.create(
            student=self.student,
            course=self.course,
            score=Decimal("80.00"),
            max_score=Decimal("100.00"),
        )

    def test_certificate_hash_is_valid_sha256(self):
        """Issued certificate_hash is a 64-character lowercase hex SHA-256 string."""
        generator = CertificateGenerator()
        certificate = generator.issue_certificate(self.student, self.course)
        self.assertEqual(len(certificate.certificate_hash), 64)
        self.assertIsNotNone(
            re.fullmatch(r"[0-9a-f]{64}", certificate.certificate_hash)
        )
