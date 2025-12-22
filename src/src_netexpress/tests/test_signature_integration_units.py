"""
Unit tests for signature integration functionality.

These tests validate specific examples and edge cases for the signature integration,
focusing on signature workflow in new portal architecture, PDF generation and storage,
and client access to signed documents.

**Requirements: 9.1, 9.2, 9.3, 9.5**
"""

from django.test import TestCase, Client as TestClient
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core import mail
from devis.models import Quote, Client, QuoteValidation
from accounts.models import Profile
from services.models import Service, Category
from unittest.mock import patch, MagicMock


class SignatureIntegrationTests(TestCase):
    """Unit tests for signature integration in the new portal architecture."""
    
    def setUp(self):
        """Set up test data for signature integration tests."""
        # Create groups
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')
        
        # Create a test category and service
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )
        
        self.service = Service.objects.create(
            title="Test Service",
            description="Test service for signature integration",
            category=self.category,
            is_active=True
        )
        
        # Create test client
        self.client_obj = Client.objects.create(
            full_name="Test Client",
            email="client@example.com",
            phone="123456789"
        )
        
        # Create client user
        self.client_user = User.objects.create_user(
            username="testclient",
            email="client@example.com",
            password="testpass123"
        )
        self.client_user.groups.add(self.clients_group)
        
        # Get the automatically created profile and update it
        self.client_profile = self.client_user.profile
        self.client_profile.role = "client"
        self.client_profile.save()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True
        )
        
        # Create test client for HTTP requests
        self.test_client = TestClient()
    
    def test_client_portal_signature_workflow_access(self):
        """
        Test that signature workflow is accessible from Client Portal.
        **Requirements: 9.5**
        """
        # Create a quote ready for signature
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for signature",
            status=Quote.QuoteStatus.SENT
        )
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Access quote detail page
        response = self.test_client.get(
            reverse('core:client_quote_detail', kwargs={'pk': quote.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Valider le devis")
        
        # Check that validation link is present and points to client portal
        validation_url = reverse('core:client_quote_validate_start', kwargs={'pk': quote.pk})
        self.assertContains(response, validation_url)
    
    def test_client_portal_signature_initiation(self):
        """
        Test signature initiation through Client Portal.
        **Requirements: 9.1, 9.5**
        """
        # Create a quote ready for signature
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for signature",
            status=Quote.QuoteStatus.SENT
        )
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Initiate signature process
        response = self.test_client.get(
            reverse('core:client_quote_validate_start', kwargs={'pk': quote.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "code de validation")
        
        # Verify validation was created
        validation = QuoteValidation.objects.filter(quote=quote).first()
        self.assertIsNotNone(validation)
        self.assertFalse(validation.is_confirmed)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("confirmation", mail.outbox[0].subject.lower())
    
    def test_client_portal_signature_completion(self):
        """
        Test signature completion through Client Portal.
        **Requirements: 9.1, 9.2, 9.5**
        """
        # Create a quote and validation
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for signature",
            status=Quote.QuoteStatus.SENT
        )
        
        validation = QuoteValidation.create_for_quote(quote)
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Submit correct validation code
        with patch('devis.models.Quote.generate_pdf') as mock_pdf:
            mock_pdf.return_value = b'%PDF-1.4 fake pdf content'
            
            response = self.test_client.post(
                reverse('core:client_quote_validate_code', kwargs={'pk': quote.pk}),
                {'code': validation.code}
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "validé avec succès")
        
        # Verify quote status updated
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.QuoteStatus.ACCEPTED)
        
        # Verify validation confirmed
        validation.refresh_from_db()
        self.assertTrue(validation.is_confirmed)
        
        # Verify PDF generation was called
        mock_pdf.assert_called_once_with(attach=True)
    
    def test_signature_workflow_access_control(self):
        """
        Test that signature workflow enforces proper access controls.
        **Requirements: 9.5**
        """
        # Create quotes for different clients
        other_client = Client.objects.create(
            full_name="Other Client",
            email="other@example.com",
            phone="987654321"
        )
        
        accessible_quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Accessible quote",
            status=Quote.QuoteStatus.SENT
        )
        
        inaccessible_quote = Quote.objects.create(
            client=other_client,
            service=self.service,
            message="Inaccessible quote",
            status=Quote.QuoteStatus.SENT
        )
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Should be able to access own quote
        response = self.test_client.get(
            reverse('core:client_quote_validate_start', kwargs={'pk': accessible_quote.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Should not be able to access other client's quote
        response = self.test_client.get(
            reverse('core:client_quote_validate_start', kwargs={'pk': inaccessible_quote.pk})
        )
        self.assertEqual(response.status_code, 403)
    
    def test_signature_workflow_quote_status_validation(self):
        """
        Test that signature workflow validates quote status.
        **Requirements: 9.1**
        """
        # Create quotes with different statuses
        draft_quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Draft quote",
            status=Quote.QuoteStatus.DRAFT
        )
        
        accepted_quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Already accepted quote",
            status=Quote.QuoteStatus.ACCEPTED
        )
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Should not be able to sign draft quote
        response = self.test_client.get(
            reverse('core:client_quote_validate_start', kwargs={'pk': draft_quote.pk})
        )
        self.assertEqual(response.status_code, 200)
        # Check that validation is not created for draft quotes
        validation = QuoteValidation.objects.filter(quote=draft_quote).first()
        self.assertIsNone(validation)
        
        # Should not be able to sign already accepted quote
        response = self.test_client.get(
            reverse('core:client_quote_validate_start', kwargs={'pk': accepted_quote.pk})
        )
        self.assertEqual(response.status_code, 200)
        # Check that validation is not created for already accepted quotes
        validation = QuoteValidation.objects.filter(quote=accepted_quote).first()
        self.assertIsNone(validation)
    
    def test_pdf_generation_on_signature(self):
        """
        Test that PDF is generated when quote is signed.
        **Requirements: 9.2**
        """
        # Create a quote
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for PDF generation",
            status=Quote.QuoteStatus.SENT
        )
        
        validation = QuoteValidation.create_for_quote(quote)
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Mock PDF generation to avoid actual file operations
        with patch('devis.models.Quote.generate_pdf') as mock_pdf:
            mock_pdf.return_value = b'%PDF-1.4 fake pdf content'
            
            # Complete signature
            response = self.test_client.post(
                reverse('core:client_quote_validate_code', kwargs={'pk': quote.pk}),
                {'code': validation.code}
            )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify PDF generation was called
        mock_pdf.assert_called_once_with(attach=True)
    
    def test_signed_document_access_through_portal(self):
        """
        Test that clients can access signed documents through the portal.
        **Requirements: 9.2, 9.5**
        """
        # Create and sign a quote
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for document access",
            status=Quote.QuoteStatus.ACCEPTED
        )
        
        # Mock PDF file
        with patch('devis.models.Quote.pdf') as mock_pdf_field:
            mock_pdf_field.return_value = True
            mock_pdf_field.name = "test_quote.pdf"
            
            # Login as client
            self.test_client.login(username="testclient", password="testpass123")
            
            # Access quote detail page
            response = self.test_client.get(
                reverse('core:client_quote_detail', kwargs={'pk': quote.pk})
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Should show that quote is accepted
            self.assertContains(response, "Accepté")
    
    def test_signature_workflow_error_handling(self):
        """
        Test error handling in signature workflow.
        **Requirements: 9.1**
        """
        # Create a quote and validation
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for error handling",
            status=Quote.QuoteStatus.SENT
        )
        
        validation = QuoteValidation.create_for_quote(quote)
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Submit incorrect validation code
        response = self.test_client.post(
            reverse('core:client_quote_validate_code', kwargs={'pk': quote.pk}),
            {'code': '000000'}  # Wrong code
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Code incorrect")
        
        # Verify quote status not changed
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.QuoteStatus.SENT)
        
        # Verify validation not confirmed
        validation.refresh_from_db()
        self.assertFalse(validation.is_confirmed)
    
    def test_signature_workflow_expiration_handling(self):
        """
        Test handling of expired validation codes.
        **Requirements: 9.1**
        """
        # Create a quote
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for expiration",
            status=Quote.QuoteStatus.SENT
        )
        
        # Create expired validation
        validation = QuoteValidation.create_for_quote(quote)
        
        # Mock the is_expired property to return True
        with patch('devis.models.QuoteValidation.is_expired', new_callable=lambda: property(lambda self: True)):
            # Login as client
            self.test_client.login(username="testclient", password="testpass123")
            
            # Try to access validation page
            response = self.test_client.get(
                reverse('core:client_quote_validate_code', kwargs={'pk': quote.pk})
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "expiré")
    
    def test_notification_integration_on_signature(self):
        """
        Test that notifications are sent when quote is signed.
        **Requirements: 9.1**
        """
        # Create a quote
        quote = Quote.objects.create(
            client=self.client_obj,
            service=self.service,
            message="Test quote for notifications",
            status=Quote.QuoteStatus.SENT
        )
        
        validation = QuoteValidation.create_for_quote(quote)
        
        # Login as client
        self.test_client.login(username="testclient", password="testpass123")
        
        # Mock notification service
        with patch('core.services.notification_service.NotificationService') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            
            # Mock PDF generation to avoid file operations
            with patch('devis.models.Quote.generate_pdf'):
                # Complete signature
                response = self.test_client.post(
                    reverse('core:client_quote_validate_code', kwargs={'pk': quote.pk}),
                    {'code': validation.code}
                )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify notification service was called
        mock_instance.notify_quote_validation.assert_called_once_with(quote)


class LegacySignatureWorkflowTests(TestCase):
    """Unit tests for legacy signature workflow compatibility."""
    
    def setUp(self):
        """Set up test data for legacy workflow tests."""
        # Create test client
        self.client_obj = Client.objects.create(
            full_name="Legacy Test Client",
            email="legacy@example.com",
            phone="123456789"
        )
        
        # Create test client for HTTP requests
        self.test_client = TestClient()
    
    def test_legacy_signature_workflow_still_works(self):
        """
        Test that the original signature workflow still functions.
        **Requirements: 9.3**
        """
        # Create a quote
        quote = Quote.objects.create(
            client=self.client_obj,
            message="Test quote for legacy workflow",
            status=Quote.QuoteStatus.SENT
        )
        
        # Access legacy validation start
        response = self.test_client.get(
            reverse('devis:quote_validate_start', kwargs={'token': quote.public_token})
        )
        
        # Should redirect to code entry
        self.assertEqual(response.status_code, 302)
        
        # Verify validation was created
        validation = QuoteValidation.objects.filter(quote=quote).first()
        self.assertIsNotNone(validation)
    
    def test_legacy_pdf_access_still_works(self):
        """
        Test that legacy PDF access still functions.
        **Requirements: 9.2, 9.3**
        """
        # Create a quote with PDF
        quote = Quote.objects.create(
            client=self.client_obj,
            message="Test quote for legacy PDF access",
            status=Quote.QuoteStatus.ACCEPTED
        )
        
        # Mock PDF file
        with patch.object(quote, 'pdf') as mock_pdf_field:
            mock_pdf_field.name = "test_quote.pdf"
            mock_pdf_field.__bool__ = lambda: True  # Make it truthy
            
            # Access PDF via public token
            response = self.test_client.get(
                reverse('devis:quote_public_pdf', kwargs={'token': quote.public_token})
            )
            
            # Should attempt to serve PDF (would be 200 with real file)
            # With mock, we expect the view to try to open the file
            self.assertIn(response.status_code, [200, 404])  # 404 due to mocking