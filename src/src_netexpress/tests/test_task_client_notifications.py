from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from accounts.models import Profile
from core.models import UINotification
from devis.models import Client
from tasks.models import Task


User = get_user_model()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class TaskClientNotificationTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client_notify',
            email='client-notify@example.com',
            password='testpass123',
        )
        profile, _ = Profile.objects.get_or_create(user=self.client_user)
        profile.role = Profile.ROLE_CLIENT
        profile.save()

        self.worker_user = User.objects.create_user(
            username='worker_notify',
            email='worker-notify@example.com',
            password='testpass123',
        )

        self.client_record = Client.objects.create(
            full_name='Client Notifications',
            email='client-notify@example.com',
            phone='0594000000',
        )

    @patch('tasks.signals.EmailNotificationService.send')
    def test_task_status_change_to_in_progress_notifies_client(self, _mock_admin_email):
        task = Task.objects.create(
            title='Intervention démarrage',
            client=self.client_record,
            start_date=date.today() + timedelta(days=2),
            due_date=date.today() + timedelta(days=7),
        )
        mail.outbox.clear()

        task.start_date = date.today()
        task.status = Task.STATUS_IN_PROGRESS
        task.save()

        notification = UINotification.objects.get(user=self.client_user, notification_type='task_updated')
        self.assertIn('Intervention en cours', notification.title)
        self.assertIn(task.title, notification.message)
        self.assertEqual(notification.link_url, '/client/tasks/')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(task.title, mail.outbox[0].subject)
        self.assertIn('Voir mes interventions', mail.outbox[0].alternatives[0][0])

    @patch('tasks.signals.EmailNotificationService.send')
    def test_task_status_change_to_completed_notifies_client(self, _mock_admin_email):
        task = Task.objects.create(
            title='Intervention clôture',
            client=self.client_record,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            status=Task.STATUS_IN_PROGRESS,
        )
        mail.outbox.clear()

        task.status = Task.STATUS_COMPLETED
        task.completed_by = self.worker_user
        task.save()

        notification = UINotification.objects.get(user=self.client_user, notification_type='task_completed')
        self.assertIn('Intervention terminée', notification.title)
        self.assertEqual(notification.link_url, '/client/tasks/')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Intervention terminée', mail.outbox[0].subject)

    @patch('tasks.signals.EmailNotificationService.send')
    def test_follow_up_save_without_status_change_does_not_duplicate_client_notification(self, _mock_admin_email):
        task = Task.objects.create(
            title='Intervention stable',
            client=self.client_record,
            start_date=date.today() + timedelta(days=2),
            due_date=date.today() + timedelta(days=7),
        )

        task.start_date = date.today()
        task.status = Task.STATUS_IN_PROGRESS
        task.save()

        mail.outbox.clear()
        task.title = 'Intervention stable mise à jour'
        task.save()

        self.assertEqual(UINotification.objects.filter(user=self.client_user, notification_type='task_updated').count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    @patch('tasks.signals.EmailNotificationService.send')
    def test_other_status_changes_do_not_notify_client(self, _mock_admin_email):
        task = Task.objects.create(
            title='Intervention sans notification client',
            client=self.client_record,
            start_date=date.today() + timedelta(days=3),
            due_date=date.today() + timedelta(days=5),
        )
        mail.outbox.clear()

        task.start_date = date.today() + timedelta(days=1)
        task.due_date = date.today() + timedelta(days=1)
        task.status = Task.STATUS_ALMOST_OVERDUE
        task.save()

        self.assertFalse(UINotification.objects.filter(user=self.client_user).exists())
        self.assertEqual(len(mail.outbox), 0)