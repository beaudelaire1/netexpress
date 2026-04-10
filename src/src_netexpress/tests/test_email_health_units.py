from smtplib import SMTPAuthenticationError
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import Client as DjangoClient, TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from core.services.email_health_service import EmailHealthService


def ensure_profile(user, role):
    profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': role})
    profile.role = role
    profile.save()
    return profile


class EmailHealthServiceTests(TestCase):
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp-relay.brevo.com',
        EMAIL_PORT=587,
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
        DEFAULT_FROM_EMAIL='ops@example.com',
        SITE_URL='https://netexpress.test',
    )
    def test_configuration_report_flags_missing_smtp_credentials(self):
        report = EmailHealthService.get_configuration_report()

        self.assertEqual(report['status'], 'critical')
        self.assertEqual(report['mode_label'], 'SMTP Brevo')
        self.assertTrue(any('SMTP' in issue for issue in report['issues']))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp-relay.brevo.com',
        EMAIL_PORT=587,
        EMAIL_HOST_USER='xsmtp-user',
        EMAIL_HOST_PASSWORD='xsmtp-password',
        DEFAULT_FROM_EMAIL='ops@example.com',
        SITE_URL='https://netexpress.test',
    )
    @patch('core.services.email_health_service.get_connection')
    def test_probe_delivery_backend_validates_smtp_connection(self, mock_get_connection):
        mock_connection = Mock()
        mock_get_connection.return_value = mock_connection

        result = EmailHealthService.probe_delivery_backend()

        self.assertEqual(result['status'], 'healthy')
        self.assertEqual(result['title'], 'Probe SMTP réussi')
        mock_connection.open.assert_called_once()
        mock_connection.close.assert_called_once()

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp-relay.brevo.com',
        EMAIL_PORT=587,
        EMAIL_HOST_USER='xsmtp-user',
        EMAIL_HOST_PASSWORD='bad-password',
        DEFAULT_FROM_EMAIL='ops@example.com',
        SITE_URL='https://netexpress.test',
    )
    @patch('core.services.email_health_service.get_connection')
    def test_probe_delivery_backend_reports_smtp_auth_failure(self, mock_get_connection):
        mock_connection = Mock()
        mock_connection.open.side_effect = SMTPAuthenticationError(535, b'Authentication failed')
        mock_get_connection.return_value = mock_connection

        result = EmailHealthService.probe_delivery_backend()

        self.assertEqual(result['status'], 'critical')
        self.assertIn('authentification SMTP', result['title'])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='ops@example.com',
        SITE_URL='https://netexpress.test',
    )
    def test_send_test_email_uses_active_backend(self):
        mail.outbox = []

        result = EmailHealthService.send_test_email('deliver@example.com')

        self.assertIn(result['status'], {'healthy', 'warning'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['deliver@example.com'])


class AdminEmailHealthViewTests(TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.admin_user = User.objects.create_user(
            username='admin_mail',
            email='admin-mail@example.com',
            password='testpass123',
            is_staff=True,
        )
        ensure_profile(self.admin_user, Profile.ROLE_ADMIN_BUSINESS)

        self.standard_user = User.objects.create_user(
            username='client_mail',
            email='client-mail@example.com',
            password='testpass123',
        )
        ensure_profile(self.standard_user, Profile.ROLE_CLIENT)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='ops@example.com',
        SITE_URL='https://netexpress.test',
    )
    def test_admin_email_health_page_renders(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('core:admin_email_health'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_email_health.html')
        self.assertIn('email_health', response.context)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='ops@example.com',
        SITE_URL='https://netexpress.test',
    )
    def test_admin_email_health_can_send_test_email(self):
        mail.outbox = []
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse('core:admin_email_health'),
            {
                'action': 'send_test_email',
                'recipient_email': 'deliver@example.com',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(response.context['test_result']['status'] in {'healthy', 'warning'})
        self.assertEqual(mail.outbox[0].to, ['deliver@example.com'])

    def test_non_admin_cannot_access_email_health_page(self):
        self.client.force_login(self.standard_user)

        response = self.client.get(reverse('core:admin_email_health'))

        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse('core:admin_email_health'))