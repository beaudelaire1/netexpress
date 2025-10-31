"""Signal handlers for the tasks application.

These handlers send notification emails whenever a task's status
changes or when a task approaches its deadline.  The emails are
addressed to a configurable recipient defined by the
``TASK_NOTIFICATION_EMAIL`` setting.  If this setting is absent the
``EMAIL_HOST_USER`` setting is used as a fallback.

The notifications use the :class:`EmailNotificationService` utility
defined in ``tasks.services`` to send messages via the configured
SMTP server.  Both the subject and body of the notifications are
kept deliberately short so that administrators can quickly
understand what has changed.
"""

from __future__ import annotations

from datetime import date
from django.conf import settings
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Task
from .services import EmailNotificationService


def _get_notification_recipient() -> str | None:
    """Return the configured recipient for task notifications.

    The ``TASK_NOTIFICATION_EMAIL`` setting takes precedence.  If it
    is not defined or empty then the ``EMAIL_HOST_USER`` setting is
    returned.  If neither is defined the function returns ``None`` and
    no notification will be sent.
    """
    to = getattr(settings, "TASK_NOTIFICATION_EMAIL", "")
    if not to:
        to = getattr(settings, "EMAIL_HOST_USER", "")
    return to or None


@receiver(pre_save, sender=Task)
def notify_status_change(sender, instance: Task, **kwargs) -> None:
    """Send a notification email when a task changes status.

    If the task is being created there is no previous state to compare
    against and no notification is sent.  When the status field
    changes from any value to another (including to ``completed``)
    this handler sends an email describing the change.  The email
    includes the task title, the previous status and the new status.
    """
    # Skip notifications when creating a new task
    if instance.pk is None:
        return
    try:
        old = Task.objects.get(pk=instance.pk)
    except Task.DoesNotExist:
        return
    if old.status != instance.status:
        recipient = _get_notification_recipient()
        if not recipient:
            return
        subject = f"Mise à jour de la tâche : {instance.title}"
        body = (
            f"La tâche \"{instance.title}\" a changé de statut.\n\n"
            f"Ancien statut : {old.get_status_display()}\n"
            f"Nouveau statut : {instance.get_status_display()}\n"
            f"Date d'échéance : {instance.due_date.strftime('%d/%m/%Y')}"
        )
        EmailNotificationService.send(recipient, subject, body)


@receiver(post_save, sender=Task)
def notify_due_soon(sender, instance: Task, **kwargs) -> None:
    """Send a reminder email when a task is approaching its deadline.

    After each save operation (creation or update) this handler checks
    if the task is due within three days and not yet completed.
    Overdue tasks are excluded to avoid duplicate notifications.  An
    email reminder is sent only when the task becomes due soon (i.e.
    when saving brings it within the threshold).  A naive approach is
    used: reminders may be sent multiple times if the task is saved
    repeatedly while still within the threshold.  For production use
    consider tracking whether a reminder has already been sent.
    """
    # Do not notify for completed or overdue tasks
    if instance.status in {Task.STATUS_COMPLETED, Task.STATUS_OVERDUE}:
        return
    # Only send a reminder if due soon
    if not instance.is_due_soon():
        return
    recipient = _get_notification_recipient()
    if not recipient:
        return
    remaining_days = (instance.due_date - date.today()).days
    subject = f"Rappel : tâche bientôt due — {instance.title}"
    body = (
        f"La tâche \"{instance.title}\" doit être terminée dans {remaining_days} jour(s).\n\n"
        f"Statut actuel : {instance.get_status_display()}\n"
        f"Échéance : {instance.due_date.strftime('%d/%m/%Y')}\n"
        f"Lieu : {instance.location or 'Non spécifié'}\n"
        f"Équipe : {instance.team or 'Non spécifié'}"
    )
    EmailNotificationService.send(recipient, subject, body)
