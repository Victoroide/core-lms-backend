"""Reusable model mixins for the Core LMS platform."""

from django.db import models


class SoftDeleteMixin(models.Model):
    """Mixin providing soft delete capability for domain models.

    Instead of issuing a SQL DELETE, records are marked with
    ``is_deleted=True`` and a ``deleted_at`` timestamp. The default
    manager excludes soft-deleted rows so they are invisible to
    normal queries while remaining recoverable.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft-delete: mark as deleted instead of issuing SQL DELETE."""
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently remove this record from the database."""
        super().delete(using=using, keep_parents=keep_parents)


class SoftDeleteManager(models.Manager):
    """Default manager that excludes soft-deleted records."""

    def get_queryset(self):
        """Return only non-deleted records.

        Returns:
            QuerySet: Filtered queryset excluding soft-deleted rows.
        """
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Unfiltered manager that includes soft-deleted records."""

    def get_queryset(self):
        """Return all records including soft-deleted ones.

        Returns:
            QuerySet: Unfiltered queryset.
        """
        return super().get_queryset()
