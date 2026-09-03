from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from core.services import notification_service
from .models import Task
from .services import EmailNotificationService, get_task_notification_recipient


logger = logging.getLogger(__name__)


def _task_admin_url(task: Task) -> str:
    return f"/admin/tasks/task/{task.pk}/change/"


def _task_action_url(task: Task) -> str | None:
    from django.conf import settings

    site_url = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return f"{site_url}{task.get_absolute_url()}" if site_url else None


@receiver(pre_save, sender=Task)
def capture_previous_status(sender, instance: Task, **kwargs) -> None:
    """Mémorise le statut en base avant la sauvegarde pour détecter une transition."""
    if instance.pk is None:
        return

    try:
        previous = Task.objects.only("status").get(pk=instance.pk)
    except Task.DoesNotExist:
        return

    instance._previous_status = previous.status


@receiver(post_save, sender=Task)
def notify_status_change(sender, instance: Task, created: bool, **kwargs) -> None:
    """Notifie après persistance lorsqu'une tâche change réellement de statut."""
    if created:
        return

    previous_status = getattr(instance, "_previous_status", None)
    if not previous_status or previous_status == instance.status:
        if hasattr(instance, "_previous_status"):
            delattr(instance, "_previous_status")
        return

    try:
        recipient = get_task_notification_recipient()
        if recipient:
            sent = EmailNotificationService.send(
                to=recipient,
                subject=f"Tâche mise à jour — {instance.title}",
                headline="Tâche mise à jour",
                intro=f"La tâche <strong>{instance.title}</strong> a changé de statut.",
                rows=[
                    {
                        "label": "Ancien statut",
                        "value": dict(Task.STATUS_CHOICES).get(previous_status, previous_status),
                    },
                    {
                        "label": "Nouveau statut",
                        "value": instance.get_status_display(),
                    },
                    {
                        "label": "Échéance",
                        "value": str(instance.due_date) if instance.due_date else "—",
                    },
                ],
                action_url=_task_action_url(instance),
                action_label="Voir la tâche",
            )
            if not sent:
                logger.warning(
                    "Task status email was not delivered | task_id=%s | recipient=%s",
                    instance.pk,
                    recipient,
                )
        else:
            logger.error(
                "Task status notification skipped: TASK_NOTIFICATION_EMAIL is not configured | task_id=%s",
                instance.pk,
            )

        if instance.status == Task.STATUS_COMPLETED:
            actor = instance.completed_by
            actor_label = (
                actor.get_full_name() or actor.username
                if actor is not None
                else "un utilisateur"
            )
            for admin in User.objects.filter(is_staff=True, is_active=True):
                try:
                    notification_service.create_ui_notification(
                        user=admin,
                        title=f"Tâche terminée: {instance.title}",
                        message=(
                            f"La tâche '{instance.title}' a été marquée comme terminée "
                            f"par {actor_label}."
                        ),
                        notification_type="task_completed",
                        link_url=_task_admin_url(instance),
                    )
                except Exception:
                    logger.exception(
                        "Admin UI notification creation failed | task_id=%s | user_id=%s",
                        instance.pk,
                        admin.pk,
                    )

        try:
            notification_service.notify_client_task_status_update(
                instance,
                previous_status=previous_status,
            )
        except Exception:
            logger.exception(
                "Client task-status notification failed | task_id=%s | previous_status=%s | new_status=%s",
                instance.pk,
                previous_status,
                instance.status,
            )
    finally:
        if hasattr(instance, "_previous_status"):
            delattr(instance, "_previous_status")


@receiver(m2m_changed, sender=Task.assigned_to.through)
def notify_task_assignment(
    sender,
    instance,
    action: str,
    reverse: bool,
    model,
    pk_set,
    **kwargs,
) -> None:
    """Crée la notification UI et l'e-mail lors d'une nouvelle affectation."""
    if action != "post_add" or not pk_set:
        return

    if reverse:
        worker = instance
        assignments = ((task, worker) for task in Task.objects.filter(pk__in=pk_set))
    else:
        task = instance
        assignments = (
            (task, worker)
            for worker in User.objects.filter(pk__in=pk_set, is_active=True)
        )

    for task, worker in assignments:
        if not getattr(worker, "is_active", False):
            continue

        try:
            notification_service.create_ui_notification(
                user=worker,
                title=f"Nouvelle tâche assignée: {task.title}",
                message=f"Une nouvelle tâche '{task.title}' vous a été assignée.",
                notification_type="task_assigned",
                link_url="/worker/dashboard/",
            )
        except Exception:
            logger.exception(
                "Task assignment UI notification failed | task_id=%s | user_id=%s",
                task.pk,
                worker.pk,
            )

        if worker.email:
            sent = EmailNotificationService.send_with_template(
                to_email=worker.email,
                subject=f"Nouvelle tâche assignée: {task.title}",
                template_name="emails/task_assignment.html",
                context={
                    "task": task,
                    "worker": worker,
                    "company_name": "NetExpress",
                },
            )
            if not sent:
                logger.warning(
                    "Task assignment email was not delivered | task_id=%s | user_id=%s | recipient=%s",
                    task.pk,
                    worker.pk,
                    worker.email,
                )
