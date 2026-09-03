from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import UINotification
from tasks.models import Task


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notifications@example.test",
    SITE_URL="https://example.test",
)
class TaskNotificationDeliveryTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.worker = User.objects.create_user(
            username="worker_delivery",
            email="worker-delivery@example.test",
            password="testpass123",
        )

    def _task(self, *, title="Intervention", due_in=7, status=Task.STATUS_UPCOMING):
        return Task.objects.create(
            title=title,
            start_date=self.today + timedelta(days=1),
            due_date=self.today + timedelta(days=due_in),
            status=status,
        )

    def test_worker_assignment_creates_ui_notification_and_email(self):
        task = self._task(title="Affectation test")
        mail.outbox.clear()

        task.assigned_to.add(self.worker)

        notification = UINotification.objects.get(
            user=self.worker,
            notification_type="task_assigned",
        )
        self.assertIn(task.title, notification.title)
        self.assertEqual(notification.link_url, "/worker/dashboard/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.worker.email])
        self.assertIn(task.title, mail.outbox[0].subject)

    @override_settings(TASK_NOTIFICATION_EMAIL="operations@example.test")
    def test_status_change_uses_explicit_internal_recipient(self):
        task = self._task(title="Transition test")
        mail.outbox.clear()

        task.start_date = self.today
        task.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["operations@example.test"])
        self.assertIn("Tâche mise à jour", mail.outbox[0].subject)

    @override_settings(TASK_NOTIFICATION_EMAIL="operations@example.test")
    def test_due_task_command_sends_only_tasks_in_window(self):
        due_task = self._task(title="Échéance proche", due_in=2)
        self._task(title="Échéance lointaine", due_in=8)
        self._task(
            title="Déjà terminée",
            due_in=1,
            status=Task.STATUS_COMPLETED,
        )
        mail.outbox.clear()

        call_command("notify_due_tasks", days=3)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["operations@example.test"])
        self.assertIn(due_task.title, mail.outbox[0].subject)

    @override_settings(TASK_NOTIFICATION_EMAIL="")
    def test_due_task_command_fails_when_recipient_is_missing(self):
        with self.assertRaises(CommandError):
            call_command("notify_due_tasks", days=3)
