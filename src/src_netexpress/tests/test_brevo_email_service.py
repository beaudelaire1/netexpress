"""
Tests for Brevo email service with Django template support.
"""
from django.test import TestCase, override_settings
from unittest.mock import Mock, patch, MagicMock, call
from core.services.brevo_email_service import BrevoEmailService
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


class BrevoEmailServiceTest(TestCase):
    """Tests for Brevo email service."""
    
    def setUp(self):
        """Initial test configuration."""
        self.api_key = 'xkeysib-test-key-12345'
        self.test_settings = {
            'BREVO_API_KEY': self.api_key,
            'DEFAULT_FROM_EMAIL': 'noreply@nettoyageexpresse.fr',
            'DEFAULT_FROM_NAME': 'Nettoyage Express'
        }
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_email_service.sib_api_v3_sdk')
    def test_service_initialization(self, mock_sib):
        """Test service initialization."""
        # Mock de la configuration
        mock_config = Mock()
        mock_api_client = Mock()
        mock_transac_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_transac_api
        
        service = BrevoEmailService()
        
        self.assertIsNotNone(service.api_key)
        self.assertEqual(service.api_key, self.api_key)
        self.assertIsNotNone(service.api_instance)
        mock_sib.Configuration.assert_called_once()
    
    @override_settings(BREVO_API_KEY='')
    def test_service_initialization_without_key(self):
        """Test that service initializes even without API key (for fallback)."""
        service = BrevoEmailService()
        self.assertIsNone(service.api_instance)
    
    @override_settings(
        BREVO_API_KEY='xkeysib-test-key-12345',
        DEFAULT_FROM_EMAIL='test@example.com',
        DEFAULT_FROM_NAME='Test Sender'
    )
    @patch('core.services.brevo_email_service.sib_api_v3_sdk')
    def test_send_email(self, mock_sib):
        """Test sending a simple email."""
        # Mock de la configuration et de l'API
        mock_config = Mock()
        mock_api_client = Mock()
        mock_transac_api = Mock()
        mock_response = Mock()
        mock_response.message_id = 'test-message-id-123'
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_transac_api
        mock_sib.SendSmtpEmail = MagicMock()
        mock_transac_api.send_transac_email.return_value = mock_response
        
        service = BrevoEmailService()
        
        # Envoyer l'email
        result = service.send(
            to_email='recipient@example.com',
            subject='Test Subject',
            body='Test body text',
            html_body='<p>Test HTML body</p>'
        )
        
        self.assertTrue(result)
        mock_transac_api.send_transac_email.assert_called_once()
    
    @override_settings(
        BREVO_API_KEY='xkeysib-test-key-12345',
        DEFAULT_FROM_EMAIL='test@example.com'
    )
    @patch('core.services.brevo_email_service.sib_api_v3_sdk')
    def test_send_email_with_attachment(self, mock_sib):
        """Test sending an email with attachment."""
        # Mock de la configuration et de l'API
        mock_config = Mock()
        mock_api_client = Mock()
        mock_transac_api = Mock()
        mock_response = Mock()
        mock_response.message_id = 'test-message-id-456'
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_transac_api
        mock_sib.SendSmtpEmail = MagicMock()
        mock_transac_api.send_transac_email.return_value = mock_response
        
        service = BrevoEmailService()
        
        # Test attachment data
        attachment_data = b'PDF content here'
        
        # Send email with attachment
        result = service.send(
            to_email='recipient@example.com',
            subject='Test with attachment',
            body='Test body',
            attachments=[('test.pdf', attachment_data)]
        )
        
        self.assertTrue(result)
        mock_transac_api.send_transac_email.assert_called_once()
    
    @override_settings(
        BREVO_API_KEY='xkeysib-test-key-12345',
        INVOICE_BRANDING={'name': 'Test Company'}
    )
    @patch('core.services.brevo_email_service.sib_api_v3_sdk')
    @patch('core.services.brevo_email_service.render_to_string')
    def test_send_with_django_template(self, mock_render, mock_sib):
        """Test sending an email with Django template."""
        # Mock de la configuration et de l'API
        mock_config = Mock()
        mock_api_client = Mock()
        mock_transac_api = Mock()
        mock_response = Mock()
        mock_response.message_id = 'test-message-id-789'
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_transac_api
        mock_sib.SendSmtpEmail = MagicMock()
        mock_transac_api.send_transac_email.return_value = mock_response
        
        # Mock template rendering
        mock_render.return_value = '<html><body><h1>Test Invoice</h1><p>Amount: 100€</p></body></html>'
        
        service = BrevoEmailService()
        
        # Template context
        context = {
            'invoice': {'number': 'FAC-001', 'total_ttc': 100.0},
            'branding': {'name': 'Test Company'}
        }
        
        # Send with Django template
        result = service.send_with_django_template(
            to_email='client@example.com',
            subject='Your Invoice FAC-001',
            template_name='emails/invoice_notification.html',
            context=context
        )
        
        self.assertTrue(result)
        mock_render.assert_called_once_with('emails/invoice_notification.html', context)
        mock_transac_api.send_transac_email.assert_called_once()
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_email_service.sib_api_v3_sdk')
    def test_send_email_api_error(self, mock_sib):
        """Test API error handling."""
        # Mock de la configuration et de l'API
        mock_config = Mock()
        mock_api_client = Mock()
        mock_transac_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_transac_api
        mock_sib.SendSmtpEmail = MagicMock()
        
        # Simulate API error
        mock_transac_api.send_transac_email.side_effect = ApiException(
            status=401,
            reason='Unauthorized'
        )
        
        service = BrevoEmailService()
        
        # Attempt to send email
        result = service.send(
            to_email='recipient@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        # Result should be False on error
        self.assertFalse(result)
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_email_service.sib_api_v3_sdk')
    @patch('core.services.brevo_email_service.render_to_string')
    def test_send_with_template_rendering_error(self, mock_render, mock_sib):
        """Test template rendering error handling."""
        # Mock de la configuration et de l'API
        mock_config = Mock()
        mock_api_client = Mock()
        mock_transac_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_transac_api
        
        # Simulate template rendering error
        mock_render.side_effect = Exception('Template not found')
        
        service = BrevoEmailService()
        
        # Attempt to send with non-existent template
        result = service.send_with_django_template(
            to_email='client@example.com',
            subject='Test',
            template_name='emails/nonexistent.html',
            context={}
        )
        
        # Result should be False on error
        self.assertFalse(result)
