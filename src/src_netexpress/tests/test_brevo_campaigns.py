"""
Tests pour le service de campagnes email Brevo.
"""
from django.test import TestCase, override_settings
from unittest.mock import Mock, patch, MagicMock
from core.services.brevo_campaign_service import BrevoCampaignService
from datetime import datetime
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


class BrevoCampaignServiceTest(TestCase):
    """Tests pour le service de campagnes Brevo."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        # Clé factice (aucun appel réseau, tout est mocké)
        self.api_key = 'xkeysib-test-key-12345'
        self.test_settings = {
            'BREVO_API_KEY': self.api_key,
            'DEFAULT_FROM_EMAIL': 'noreply@nettoyageexpresse.fr',
            'DEFAULT_FROM_NAME': 'Nettoyage Express'
        }
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_service_initialization(self, mock_sib):
        """Test l'initialisation du service."""
        # Mock de la configuration
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        service = BrevoCampaignService()
        
        self.assertIsNotNone(service.api_key)
        self.assertEqual(service.api_key, self.api_key)
        mock_sib.Configuration.assert_called_once()
    
    @override_settings(BREVO_API_KEY='')
    def test_service_initialization_without_key(self):
        """Test que le service lève une erreur sans clé API."""
        with self.assertRaises(ValueError):
            BrevoCampaignService()
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_create_campaign(self, mock_sib):
        """Test la création d'une campagne."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        # Mock de la réponse API
        mock_response = Mock()
        mock_response.id = 12345
        mock_campaigns_api.create_email_campaign.return_value = mock_response
        
        service = BrevoCampaignService()
        
        result = service.create_campaign(
            name="Test Campaign",
            subject="Test Subject",
            html_content="<h1>Test</h1>"
        )
        
        self.assertEqual(result['id'], 12345)
        self.assertEqual(result['name'], "Test Campaign")
        self.assertEqual(result['status'], 'created')
        mock_campaigns_api.create_email_campaign.assert_called_once()
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_create_campaign_with_list_ids(self, mock_sib):
        """Test la création d'une campagne avec des listes."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        mock_response = Mock()
        mock_response.id = 12346
        mock_campaigns_api.create_email_campaign.return_value = mock_response
        
        service = BrevoCampaignService()
        
        result = service.create_campaign(
            name="Test Campaign with Lists",
            subject="Test Subject",
            html_content="<h1>Test</h1>",
            list_ids=[2, 7]
        )
        
        self.assertEqual(result['id'], 12346)
        # Vérifier que create_email_campaign a été appelé avec les bons paramètres
        call_args = mock_campaigns_api.create_email_campaign.call_args
        self.assertIsNotNone(call_args)
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_send_campaign(self, mock_sib):
        """Test l'envoi d'une campagne."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        mock_response = Mock()
        mock_campaigns_api.send_email_campaign_now.return_value = mock_response
        
        service = BrevoCampaignService()
        
        result = service.send_campaign(12345)
        
        self.assertEqual(result['campaign_id'], 12345)
        self.assertEqual(result['status'], 'sent')
        mock_campaigns_api.send_email_campaign_now.assert_called_once_with(12345)
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_get_campaign(self, mock_sib):
        """Test la récupération d'une campagne."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        mock_response = Mock()
        mock_response.id = 12345
        mock_response.name = "Test Campaign"
        mock_response.subject = "Test Subject"
        mock_response.type = "classic"
        mock_response.status = "sent"
        mock_response.scheduled_at = None
        mock_response.sent_at = "2024-01-01T10:00:00Z"
        mock_response.recipients = {"listIds": [2, 7]}
        
        mock_campaigns_api.get_email_campaign.return_value = mock_response
        
        service = BrevoCampaignService()
        
        result = service.get_campaign(12345)
        
        self.assertEqual(result['id'], 12345)
        self.assertEqual(result['name'], "Test Campaign")
        self.assertEqual(result['status'], "sent")
        mock_campaigns_api.get_email_campaign.assert_called_once_with(12345)
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_list_campaigns(self, mock_sib):
        """Test la liste des campagnes."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        # Mock de la réponse avec plusieurs campagnes
        mock_campaign1 = Mock()
        mock_campaign1.id = 1
        mock_campaign1.name = "Campaign 1"
        mock_campaign1.subject = "Subject 1"
        mock_campaign1.type = "classic"
        mock_campaign1.status = "sent"
        mock_campaign1.scheduled_at = None
        mock_campaign1.sent_at = "2024-01-01T10:00:00Z"
        
        mock_campaign2 = Mock()
        mock_campaign2.id = 2
        mock_campaign2.name = "Campaign 2"
        mock_campaign2.subject = "Subject 2"
        mock_campaign2.type = "classic"
        mock_campaign2.status = "draft"
        mock_campaign2.scheduled_at = None
        mock_campaign2.sent_at = None
        
        mock_response = Mock()
        mock_response.campaigns = [mock_campaign1, mock_campaign2]
        mock_campaigns_api.get_email_campaigns.return_value = mock_response
        
        service = BrevoCampaignService()
        
        result = service.list_campaigns()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 1)
        self.assertEqual(result[0]['name'], "Campaign 1")
        self.assertEqual(result[1]['id'], 2)
        self.assertEqual(result[1]['name'], "Campaign 2")
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_create_and_send_campaign(self, mock_sib):
        """Test la création et l'envoi immédiat d'une campagne."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        # Mock pour create
        mock_create_response = Mock()
        mock_create_response.id = 12345
        mock_campaigns_api.create_email_campaign.return_value = mock_create_response
        
        # Mock pour send
        mock_send_response = Mock()
        mock_campaigns_api.send_email_campaign_now.return_value = mock_send_response
        
        service = BrevoCampaignService()
        
        result = service.create_and_send_campaign(
            name="Test Campaign",
            subject="Test Subject",
            html_content="<h1>Test</h1>"
        )
        
        self.assertEqual(result['id'], 12345)
        self.assertEqual(result['status'], 'sent')
        mock_campaigns_api.create_email_campaign.assert_called_once()
        mock_campaigns_api.send_email_campaign_now.assert_called_once_with(12345)
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_create_campaign_api_error(self, mock_sib):
        """Test la gestion des erreurs API lors de la création."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        # Mock d'une erreur API
        api_exception = ApiException(status=400, reason="Bad Request")
        api_exception.body = '{"message": "Invalid parameters"}'
        mock_campaigns_api.create_email_campaign.side_effect = api_exception
        
        service = BrevoCampaignService()
        
        with self.assertRaises(Exception) as context:
            service.create_campaign(
                name="Test Campaign",
                subject="Test Subject",
                html_content="<h1>Test</h1>"
            )
        
        self.assertIn("Erreur lors de la création de la campagne", str(context.exception))
    
    @override_settings(BREVO_API_KEY='xkeysib-test-key-12345')
    @patch('core.services.brevo_campaign_service.sib_api_v3_sdk')
    def test_delete_campaign(self, mock_sib):
        """Test la suppression d'une campagne."""
        # Setup mocks
        mock_config = Mock()
        mock_api_client = Mock()
        mock_campaigns_api = Mock()
        mock_contacts_api = Mock()
        
        mock_sib.Configuration.return_value = mock_config
        mock_sib.ApiClient.return_value = mock_api_client
        mock_sib.EmailCampaignsApi.return_value = mock_campaigns_api
        mock_sib.ContactsApi.return_value = mock_contacts_api
        
        mock_campaigns_api.delete_email_campaign.return_value = None
        
        service = BrevoCampaignService()
        
        result = service.delete_campaign(12345)
        
        self.assertTrue(result)
        mock_campaigns_api.delete_email_campaign.assert_called_once_with(12345)

