"""
Unit tests for automatic client account creation workflow.

Tests the account creation logic, email invitation sending, and password setup process.
**Validates: Requirements 6.3, 6.4**
"""

from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse

from devis.models import Client, Quote
from accounts.models import Profile
from accounts.services import ClientAccountCreationService
from core.services.email_service import EmailService

User = get_user_model()


class ClientAccountCreationServiceTests(TestCase):
    """Unit tests for ClientAccountCreationService."""
    
    def setUp(self):
        """Set up test data."""
        # Ensure Clients group exists
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        
        # Create test client
        self.test_client = Client.objects.create(
            full_name="Test Client",
            email="test@example.com",
            phone="1234567890"
        )
        
        # Create test quote
        self.test_quote = Quote.objects.create(
            client=self.test_client,
            status=Quote.QuoteStatus.DRAFT,
            issue_date=date.today(),
            total_ht=Decimal('100.00'),
            tva=Decimal('20.00'),
            total_ttc=Decimal('120.00')
        )
    
    def test_create_from_quote_validation_success(self):
        """Test successful account creation from quote validation."""
        user, created = ClientAccountCreationService.create_from_quote_validation(self.test_quote)
        
        self.assertTrue(created, "Account should be created")
        self.assertEqual(user.email, self.test_client.email)
        self.assertTrue(user.is_active)
        self.assertFalse(user.has_usable_password(), "Password should not be usable initially")
        
        # Check profile
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.role, Profile.ROLE_CLIENT)
        self.assertEqual(user.profile.phone, self.test_client.phone)
        
        # Check group membership
        self.assertTrue(user.groups.filter(name='Clients').exists())
    
    def test_create_from_quote_validation_existing_user(self):
        """Test that existing users are not duplicated."""
        # Create existing user
        existing_user = User.objects.create_user(
            username="existing",
            email=self.test_client.email,
            password="testpass123"
        )
        
        user, created = ClientAccountCreationService.create_from_quote_validation(self.test_quote)
        
        self.assertFalse(created, "Account should not be created for existing user")
        self.assertEqual(user, existing_user)
    
    def test_create_from_quote_validation_no_quote(self):
        """Test error handling when quote is None."""
        with self.assertRaises(ValidationError) as cm:
            ClientAccountCreationService.create_from_quote_validation(None)
        
        self.assertIn("Quote is required", str(cm.exception))
    
    def test_create_from_quote_validation_no_client(self):
        """Test error handling when quote has no client."""
        # Create a minimal quote object without using the model
        # since the model enforces client_id NOT NULL constraint
        class MockQuote:
            def __init__(self):
                self.client = None
        
        mock_quote = MockQuote()
        
        with self.assertRaises(ValidationError) as cm:
            ClientAccountCreationService.create_from_quote_validation(mock_quote)
        
        self.assertIn("Quote must have an associated client", str(cm.exception))
    
    def test_create_from_quote_validation_no_email(self):
        """Test error handling when client has no email."""
        client_no_email = Client.objects.create(
            full_name="No Email Client",
            email="",  # Empty email
            phone="1234567890"
        )
        
        quote_no_email = Quote.objects.create(
            client=client_no_email,
            status=Quote.QuoteStatus.DRAFT,
            issue_date=date.today()
        )
        
        with self.assertRaises(ValidationError) as cm:
            ClientAccountCreationService.create_from_quote_validation(quote_no_email)
        
        self.assertIn("Client must have an email address", str(cm.exception))
    
    def test_generate_username_unique(self):
        """Test username generation creates unique usernames."""
        # Create user with base username
        User.objects.create_user(username="test", email="other@example.com")
        
        # Generate username should create unique variant
        username = ClientAccountCreationService._generate_username("test@example.com")
        self.assertEqual(username, "test_1")
    
    def test_generate_invitation_token(self):
        """Test invitation token generation."""
        user = User.objects.create_user(username="test", email="test@example.com")
        token = ClientAccountCreationService.generate_invitation_token(user)
        
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 20)  # Should be a substantial token


class EmailInvitationTests(TestCase):
    """Unit tests for email invitation system."""
    
    def setUp(self):
        """Set up test data."""
        self.test_user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        
        self.test_client = Client.objects.create(
            full_name="Test Client",
            email="test@example.com",
            phone="1234567890"
        )
        
        self.test_quote = Quote.objects.create(
            client=self.test_client,
            status=Quote.QuoteStatus.ACCEPTED,
            issue_date=date.today(),
            total_ht=Decimal('100.00'),
            tva=Decimal('20.00'),
            total_ttc=Decimal('120.00')
        )
    
    @override_settings(TESTING=True)
    def test_send_client_invitation_success(self):
        """Test successful email invitation sending."""
        # Clear mail outbox
        mail.outbox = []
        
        result = EmailService.send_client_invitation(self.test_user, self.test_quote)
        
        self.assertTrue(result, "Email should be sent successfully")
        self.assertEqual(len(mail.outbox), 1, "One email should be sent")
        
        email = mail.outbox[0]
        self.assertIn("Bienvenue", email.subject)
        self.assertEqual(email.to, [self.test_user.email])
        self.assertIn("Configurer mon mot de passe", email.body)
    
    def test_send_client_invitation_no_email(self):
        """Test invitation sending fails gracefully for user without email."""
        user_no_email = User.objects.create_user(
            username="noemail",
            email="",  # No email
        )
        
        result = EmailService.send_client_invitation(user_no_email, self.test_quote)
        
        self.assertFalse(result, "Email sending should fail for user without email")
    
    @patch('core.services.email_service.EmailMultiAlternatives.send')
    def test_send_client_invitation_email_failure(self, mock_send):
        """Test invitation sending handles email failures gracefully."""
        mock_send.side_effect = Exception("SMTP Error")
        
        result = EmailService.send_client_invitation(self.test_user, self.test_quote)
        
        self.assertFalse(result, "Should return False on email failure")


class PasswordSetupWorkflowTests(TestCase):
    """Unit tests for password setup workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.test_user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=None  # No password set initially
        )
        # Profile is created automatically by signal, so we don't need to create it manually
    
    def test_password_setup_view_get_valid_token(self):
        """Test password setup view with valid token."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        token = default_token_generator.make_token(self.test_user)
        uid = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        
        url = reverse('accounts:password_setup', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuration du mot de passe")
        self.assertContains(response, self.test_user.email)
    
    def test_password_setup_view_invalid_token(self):
        """Test password setup view with invalid token."""
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        uid = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        invalid_token = "invalid-token"
        
        url = reverse('accounts:password_setup', kwargs={'uidb64': uid, 'token': invalid_token})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lien invalide")
    
    def test_password_setup_view_post_success(self):
        """Test successful password setup via POST."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        token = default_token_generator.make_token(self.test_user)
        uid = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        
        url = reverse('accounts:password_setup', kwargs={'uidb64': uid, 'token': token})
        
        response = self.client.post(url, {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123',
        })
        
        # Should redirect to client dashboard after successful setup
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:client_dashboard'))
        
        # User should be logged in and password should be set
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.check_password('newpassword123'))
    
    def test_password_setup_view_post_password_mismatch(self):
        """Test password setup with mismatched passwords."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        token = default_token_generator.make_token(self.test_user)
        uid = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        
        url = reverse('accounts:password_setup', kwargs={'uidb64': uid, 'token': token})
        
        response = self.client.post(url, {
            'new_password1': 'newpassword123',
            'new_password2': 'differentpassword',
        })
        
        # Should stay on the same page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuration du mot de passe")


class SignalIntegrationTests(TestCase):
    """Unit tests for signal integration with quote validation."""
    
    def setUp(self):
        """Set up test data."""
        Group.objects.get_or_create(name='Clients')
        
        self.test_client = Client.objects.create(
            full_name="Signal Test Client",
            email="signal@example.com",
            phone="1234567890"
        )
        
        self.test_quote = Quote.objects.create(
            client=self.test_client,
            status=Quote.QuoteStatus.DRAFT,
            issue_date=date.today(),
            total_ht=Decimal('100.00'),
            tva=Decimal('20.00'),
            total_ttc=Decimal('120.00')
        )
    
    @patch('accounts.services.ClientAccountCreationService.create_from_quote_validation')
    @patch('core.services.email_service.EmailService.send_client_invitation')
    @override_settings(TESTING=False)  # Enable signals
    def test_quote_validation_triggers_account_creation(self, mock_send_email, mock_create_account):
        """Test that quote validation triggers account creation via signal."""
        # Mock the service methods
        mock_user = MagicMock()
        mock_create_account.return_value = (mock_user, True)  # New account created
        mock_send_email.return_value = True
        
        # Trigger quote validation
        self.test_quote.status = Quote.QuoteStatus.ACCEPTED
        self.test_quote.save()
        
        # Verify service methods were called
        mock_create_account.assert_called_once_with(self.test_quote)
        mock_send_email.assert_called_once_with(mock_user, self.test_quote)
    
    @patch('accounts.services.ClientAccountCreationService.create_from_quote_validation')
    @patch('core.services.email_service.EmailService.send_client_invitation')
    @override_settings(TESTING=False)  # Enable signals
    def test_quote_validation_existing_account_no_email(self, mock_send_email, mock_create_account):
        """Test that existing accounts don't trigger invitation emails."""
        # Mock the service methods - existing account
        mock_user = MagicMock()
        mock_create_account.return_value = (mock_user, False)  # Existing account
        
        # Trigger quote validation
        self.test_quote.status = Quote.QuoteStatus.ACCEPTED
        self.test_quote.save()
        
        # Verify account creation was called but email was not
        mock_create_account.assert_called_once_with(self.test_quote)
        mock_send_email.assert_not_called()
    
    @patch('accounts.services.ClientAccountCreationService.create_from_quote_validation')
    @override_settings(TESTING=False)  # Enable signals
    def test_quote_validation_handles_service_errors(self, mock_create_account):
        """Test that signal handles service errors gracefully."""
        # Mock service to raise an exception
        mock_create_account.side_effect = Exception("Service error")
        
        # Trigger quote validation - should not crash
        try:
            self.test_quote.status = Quote.QuoteStatus.ACCEPTED
            self.test_quote.save()
        except Exception:
            self.fail("Quote validation should not crash due to service errors")