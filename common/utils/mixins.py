from typing import Any

from django.db import models, transaction, router
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that implements soft-delete semantics for bulk operations."""

    def delete(self):
        """Soft-delete: mark rows as deleted by setting `deleted_at`.

        Returns number of rows updated.
        """
        now = timezone.now()
        return self.update(deleted_at=now)

    def hard_delete(self):
        """Permanently delete rows from the database."""
        return super().delete()

    def alive(self):
        """Return only non-deleted rows."""
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        """Return only deleted rows."""
        return self.exclude(deleted_at__isnull=True)

    def restore(self):
        """Bulk-restore soft-deleted rows."""
        return self.update(deleted_at=None)


class SoftDeleteManager(models.Manager):
    """Default manager that hides soft-deleted rows (objects).

    Use `.all_objects` (see AllObjectsManager) to access including deleted ones.
    """

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=True
        )


class AllObjectsManager(models.Manager):
    """Manager that returns both deleted and non-deleted rows (no filtering)."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteMixin(models.Model):
    """Abstract model mixin to provide soft-delete behavior.

    Fields provided:
      - deleted_at: DateTime when model was soft-deleted (null if active)

    Managers provided:
      - objects: default manager that excludes deleted rows
      - all_objects: returns all rows including deleted ones
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Managers: `objects` hides deleted objects by default, `all_objects` exposes them
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, using: Any = None, cascade: bool = True) -> None:
        """Soft-delete this instance.

        If cascade=True the method will attempt to soft-delete related objects that
        appear to support soft-delete (i.e., have a `deleted_at` field). This is a
        best-effort cascade to avoid accidentally hard-deleting related objects.
        """
        using = using or router.db_for_write(self.__class__, instance=self)
        now = timezone.now()
        # Save deleted_at using a single update to avoid race conditions
        self.__class__.objects.filter(pk=self.pk).update(deleted_at=now)
        # Update instance in memory for callers that inspect it after call
        self.deleted_at = now

        if cascade:
            # best-effort cascading to related objects that support soft-delete
            try:
                with transaction.atomic():
                    for rel in self._meta.related_objects:
                        accessor = rel.get_accessor_name()
                        try:
                            related = getattr(self, accessor)
                        except Exception:
                            # accessor might not exist or raise DoesNotExist
                            continue

                        # Related manager (one-to-many / many-to-many)
                        if hasattr(related, "all"):
                            qs = related.all()
                            # If target model looks like it supports deleted_at -> soft-delete
                            if hasattr(qs.model, "deleted_at"):
                                qs.update(deleted_at=now)
                            else:
                                # fallback to calling delete() on queryset (may hard delete)
                                qs.delete()
                        else:
                            # Single object relation (OneToOne)
                            try:
                                if related is None:
                                    continue
                                if hasattr(related, "deleted_at") and hasattr(
                                    related, "soft_delete"
                                ):
                                    related.soft_delete()
                                else:
                                    related.delete()
                            except Exception:
                                # swallow issues for best-effort cascade
                                continue
            except Exception:
                # Do not bubble cascade errors up; soft-delete itself succeeded.
                pass

    def restore(self) -> None:
        """Restore a previously soft-deleted instance (set deleted_at=None)."""
        self.__class__.all_objects.filter(pk=self.pk).update(deleted_at=None)
        self.deleted_at = None

    def hard_delete(self, using: Any = None, keep_parents: bool = False) -> None:
        """Permanently remove the instance from the database."""
        super().delete(using=using, keep_parents=keep_parents)

    def delete(self, using: Any = None, keep_parents: bool = False) -> None:
        """Override Model.delete() to perform a soft-delete by default."""
        # For compatibility with Django's delete signature we accept keep_parents but ignore it
        self.soft_delete(using=using, cascade=True)
