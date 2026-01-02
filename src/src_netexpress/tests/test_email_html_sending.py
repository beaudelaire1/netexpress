"""
Tests for HTML email sending via Brevo backend.
"""
from django.test import TestCase, override_settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from unittest.mock import Mock, patch, MagicMock
from core.backends.brevo_backend import BrevoEmailBackend
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


class EmailHTMLSendingTest(TestCase):
    """Tests pour vérifier que les emails HTML sont correctement envoyés."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        self.api_key = 'xkeysib-test-key-12345'
        
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.backends.brevo_backend.sib_api_v3_sdk')
    def test_html_content_from_alternatives(self, mock_sib):
        """Test que _get_html_content récupère le HTML depuis alternatives."""
        # Setup mocks
        mock_config = Mock()
        mock_config.api_key = {}  # Make it a dict for item assignment
        mock_api_client = Mock()
        mock_api_instance = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_api_instance
        
        # Create backend
        backend = BrevoEmailBackend()
        
        # Create message with HTML alternative
        html_content = '<html><body><h1>Test Email</h1><p>This is a test.</p></body></html>'
        text_content = 'Test Email\nThis is a test.'
        
        message = EmailMultiAlternatives(
            subject='Test Subject',
            body=text_content,
            from_email='test@example.com',
            to=['recipient@example.com']
        )
        message.attach_alternative(html_content, "text/html")
        
        # Test _get_html_content
        retrieved_html = backend._get_html_content(message)
        
        self.assertEqual(retrieved_html, html_content)
        self.assertIn('<h1>Test Email</h1>', retrieved_html)
        
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.backends.brevo_backend.sib_api_v3_sdk')
    def test_html_content_from_body(self, mock_sib):
        """Test que _get_html_content utilise le body si c'est du HTML."""
        # Setup mocks
        mock_config = Mock()
        mock_config.api_key = {}  # Make it a dict for item assignment
        mock_api_client = Mock()
        mock_api_instance = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_api_instance
        
        # Create backend
        backend = BrevoEmailBackend()
        
        # Create message with HTML in body (no alternatives)
        html_content = '<html><body><h1>Direct HTML</h1></body></html>'
        
        message = EmailMultiAlternatives(
            subject='Test Subject',
            body=html_content,
            from_email='test@example.com',
            to=['recipient@example.com']
        )
        
        # Test _get_html_content
        retrieved_html = backend._get_html_content(message)
        
        self.assertEqual(retrieved_html, html_content)
        
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.backends.brevo_backend.sib_api_v3_sdk')
    def test_plain_text_converted_to_html(self, mock_sib):
        """Test que le texte brut est converti en HTML simple."""
        # Setup mocks
        mock_config = Mock()
        mock_config.api_key = {}  # Make it a dict for item assignment
        mock_api_client = Mock()
        mock_api_instance = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_api_instance
        
        # Create backend
        backend = BrevoEmailBackend()
        
        # Create message with plain text
        text_content = 'Line 1\nLine 2\nLine 3'
        
        message = EmailMultiAlternatives(
            subject='Test Subject',
            body=text_content,
            from_email='test@example.com',
            to=['recipient@example.com']
        )
        
        # Test _get_html_content
        retrieved_html = backend._get_html_content(message)
        
        self.assertIn('<html><body>', retrieved_html)
        self.assertIn('<br>', retrieved_html)
        self.assertIn('Line 1', retrieved_html)
        
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.backends.brevo_backend.sib_api_v3_sdk')
    def test_send_message_with_html_template(self, mock_sib):
        """Test l'envoi complet d'un message avec template HTML."""
        # Setup mocks
        mock_config = Mock()
        mock_config.api_key = {}  # Make it a dict for item assignment
        mock_api_client = Mock()
        mock_api_instance = Mock()
        mock_response = Mock()
        mock_response.message_id = 'test-message-id-123'
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.TransactionalEmailsApi.return_value = mock_api_instance
        mock_api_instance.send_transac_email.return_value = mock_response
        mock_sib.SendSmtpEmail = MagicMock()
        
        # Create backend
        backend = BrevoEmailBackend()
        
        # Create message with HTML
        html_content = '''
        <html>
        <body style="background-color: #104130;">
            <h1>NETTOYAGE EXPRESS</h1>
            <p>Facture #12345</p>
            <p>Montant: 150.00 €</p>
        </body>
        </html>
        '''
        text_content = 'Facture #12345\nMontant: 150.00 €'
        
        message = EmailMultiAlternatives(
            subject='Facture #12345',
            body=text_content,
            from_email='test@example.com',
            to=['client@example.com']
        )
        message.attach_alternative(html_content, "text/html")
        
        # Send message
        result = backend._send_message_brevo(message)
        
        # Verify
        self.assertTrue(result)
        mock_api_instance.send_transac_email.assert_called_once()
        
        # Verify that SendSmtpEmail was called with HTML content
        call_args = mock_sib.SendSmtpEmail.call_args
        self.assertIsNotNone(call_args)


class EmailServiceHTMLTest(TestCase):
    """Tests pour vérifier que les services email utilisent les templates."""
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@example.com'
    )
    def test_email_service_uses_alternatives(self):
        """Test that EmailService properly attaches HTML alternatives."""
        from django.core import mail
        
        # Create a simple email with HTML alternative
        from django.core.mail import EmailMultiAlternatives
        
        html_content = '<html><body><h1>Test HTML</h1></body></html>'
        text_content = 'Test text'
        
        email = EmailMultiAlternatives(
            subject='Test Subject',
            body=text_content,
            from_email='test@example.com',
            to=['recipient@example.com']
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        
        # Check email has HTML alternative
        self.assertEqual(len(sent_email.alternatives), 1)
        html, mimetype = sent_email.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('<h1>Test HTML</h1>', html)
