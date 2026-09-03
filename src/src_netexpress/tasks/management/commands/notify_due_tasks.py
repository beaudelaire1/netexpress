from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tasks.models import Task
from tasks.services import EmailNotificationService, get_task_notification_recipient


class Command(BaseCommand):
    help = "Envoie les rappels des tâches arrivant à échéance dans les prochains jours."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=3,
            help="Fenêtre de rappel en jours, échéance du jour incluse (défaut: 3).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Liste les tâches concernées sans envoyer d'e-mail.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        if days < 0:
            raise CommandError("--days doit être supérieur ou égal à 0.")

        recipient = get_task_notification_recipient()
        if not recipient:
            raise CommandError(
                "TASK_NOTIFICATION_EMAIL n'est pas configuré : aucun rappel ne peut être envoyé."
            )

        today = timezone.localdate()
        deadline = today + timedelta(days=days)
        tasks = list(
            Task.objects.exclude(status=Task.STATUS_COMPLETED)
            .filter(due_date__gte=today, due_date__lte=deadline)
            .order_by("due_date", "pk")
        )

        if not tasks:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Aucune tâche à échéance entre {today.isoformat()} et {deadline.isoformat()}."
                )
            )
            return

        if dry_run:
            self.stdout.write(
                f"{len(tasks)} tâche(s) à notifier à {recipient} entre "
                f"{today.isoformat()} et {deadline.isoformat()}:"
            )
            for task in tasks:
                self.stdout.write(
                    f"- #{task.pk} {task.title} — échéance {task.due_date.isoformat()}"
                )
            return

        site_url = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
        sent_count = 0
        failed_ids: list[int] = []

        for task in tasks:
            remaining = (task.due_date - today).days
            action_url = (
                f"{site_url}{task.get_absolute_url()}" if site_url else None
            )
            sent = EmailNotificationService.send(
                to=recipient,
                subject=f"Rappel — tâche proche de l'échéance ({task.title})",
                headline="Rappel : tâche proche",
                intro=(
                    f"La tâche <strong>{task.title}</strong> arrive bientôt à échéance."
                ),
                rows=[
                    {"label": "Jours restants", "value": str(remaining)},
                    {"label": "Échéance", "value": task.due_date.isoformat()},
                    {"label": "Statut", "value": task.get_status_display()},
                ],
                action_url=action_url,
                action_label="Ouvrir la tâche",
            )

            if sent:
                sent_count += 1
            else:
                failed_ids.append(task.pk)

        self.stdout.write(
            f"Rappels traités: {len(tasks)} | envoyés: {sent_count} | échecs: {len(failed_ids)}"
        )

        if failed_ids:
            raise CommandError(
                "Échec d'envoi des rappels pour les tâches: "
                + ", ".join(f"#{task_id}" for task_id in failed_ids)
            )

        self.stdout.write(self.style.SUCCESS("Tous les rappels ont été envoyés."))
