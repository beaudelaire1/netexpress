"""Mixins réutilisables pour les modèles du projet."""

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet qui exclut les objets soft-deleted par défaut."""

    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.exclude(deleted_at__isnull=True)


class SoftDeleteManager(models.Manager):
    """Manager qui ne retourne que les objets non supprimés."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteMixin(models.Model):
    """Mixin ajoutant le soft delete à un modèle.

    Utilisation :
        class MonModele(SoftDeleteMixin, models.Model):
            ...

    Le manager par défaut filtre les objets supprimés.
    `all_objects` retourne tout, y compris les supprimés.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])
