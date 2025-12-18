from __future__ import annotations

from datetime import date
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Task
from .services import EmailNotificationService


def _recipient() -> str | None:
    return (
        getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
        or getattr(settings, "EMAIL_HOST_USER", None)
        or getattr(settings, "DEFAULT_FROM_EMAIL", None)
    )


@receiver(pre_save, sender=Task)
def notify_status_change(sender, instance: Task, **kwargs) -> None:
    """Notification premium quand une tâche change de statut."""
    if instance.pk is None:
        return
    try:
        prev = Task.objects.get(pk=instance.pk)
    except Task.DoesNotExist:
        return

    if prev.status == instance.status:
        return

    to = _recipient()
    if not to:
        return

    subject = f"Tâche mise à jour — {instance.title}"
    headline = "Tâche mise à jour"
    intro = f"La tâche <strong>{instance.title}</strong> a changé de statut."
    rows = [
        {"label": "Statut", "value": dict(Task.STATUS_CHOICES).get(instance.status, instance.status)},
        {"label": "Échéance", "value": str(instance.due_date) if instance.due_date else "—"},
    ]
    EmailNotificationService.send(
        to=to,
        subject=subject,
        headline=headline,
        intro=intro,
        rows=rows,
        action_url=getattr(settings, "SITE_URL", "") + instance.get_absolute_url() if getattr(settings, "SITE_URL", "") else None,
        action_label="Voir la tâche",
    )


@receiver(post_save, sender=Task)
def notify_due_soon(sender, instance: Task, created: bool, **kwargs) -> None:
    """Rappel premium quand une tâche approche de l'échéance."""
    if instance.status == Task.STATUS_COMPLETED:
        return
    if not instance.due_date:
        return

    today = date.today()
    remaining = (instance.due_date - today).days

    # Rappel si proche (<=3 jours) mais pas en retard
    if remaining < 0:
        return
    if remaining > 3:
        return

    to = _recipient()
    if not to:
        return

    subject = f"Rappel — tâche proche de l'échéance ({instance.title})"
    headline = "Rappel : tâche proche"
    intro = f"La tâche <strong>{instance.title}</strong> arrive bientôt à échéance."
    rows = [
        {"label": "Jours restants", "value": str(remaining)},
        {"label": "Échéance", "value": str(instance.due_date)},
        {"label": "Statut", "value": dict(Task.STATUS_CHOICES).get(instance.status, instance.status)},
    ]
    EmailNotificationService.send(
        to=to,
        subject=subject,
        headline=headline,
        intro=intro,
        rows=rows,
        action_url=getattr(settings, "SITE_URL", "") + instance.get_absolute_url() if getattr(settings, "SITE_URL", "") else None,
        action_label="Ouvrir la tâche",
    )
