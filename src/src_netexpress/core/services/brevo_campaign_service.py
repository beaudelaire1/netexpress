"""
Service pour gérer les campagnes email via l'API Brevo (ex-Sendinblue).
Permet de créer et gérer des campagnes marketing en plus des emails transactionnels.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from django.conf import settings
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


class BrevoCampaignService:
    """
    Service pour créer et gérer des campagnes email via l'API Brevo.
    """
    
    def __init__(self):
        """Initialise le service avec la clé API Brevo."""
        self.api_key = getattr(settings, 'BREVO_API_KEY', None)
        
        if not self.api_key or not str(self.api_key).strip():
            raise ValueError("BREVO_API_KEY doit être configurée dans les settings")
        
        # Configuration du client API
        try:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = str(self.api_key).strip()
            self.api_client = sib_api_v3_sdk.ApiClient(configuration)
            self.campaigns_api = sib_api_v3_sdk.EmailCampaignsApi(self.api_client)
            self.contacts_api = sib_api_v3_sdk.ContactsApi(self.api_client)
            logger.info("[OK] BrevoCampaignService initialise avec succes")
        except Exception as e:
            logger.error(f"[ERROR] Erreur lors de l'initialisation de BrevoCampaignService: {e}")
            raise
    
    def create_campaign(
        self,
        name: str,
        subject: str,
        html_content: str,
        sender_name: str = None,
        sender_email: str = None,
        list_ids: List[int] = None,
        scheduled_at: Optional[datetime] = None,
        campaign_type: str = "classic"
    ) -> Dict[str, Any]:
        """
        Crée une campagne email via l'API Brevo.
        
        Args:
            name: Nom de la campagne
            subject: Sujet de l'email
            html_content: Contenu HTML de l'email
            sender_name: Nom de l'expéditeur (défaut: DEFAULT_FROM_NAME)
            sender_email: Email de l'expéditeur (défaut: DEFAULT_FROM_EMAIL)
            list_ids: Liste des IDs de listes de contacts (optionnel)
            scheduled_at: Date/heure d'envoi programmé (optionnel, None = envoi immédiat)
            campaign_type: Type de campagne ("classic" ou "trigger")
        
        Returns:
            Dict contenant les informations de la campagne créée
        
        Raises:
            ApiException: En cas d'erreur API Brevo
            ValueError: Si les paramètres sont invalides
        """
        # Valeurs par défaut pour l'expéditeur
        if not sender_email:
            sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
        if not sender_name:
            sender_name = getattr(settings, 'DEFAULT_FROM_NAME', 'Nettoyage Express')
        
        # Préparer les paramètres de la campagne
        recipients = None
        if list_ids and len(list_ids) > 0:
            recipients = {"listIds": list_ids}
        
        email_campaign = sib_api_v3_sdk.CreateEmailCampaign(
            name=name,
            subject=subject,
            sender={
                "name": sender_name,
                "email": sender_email
            },
            type=campaign_type,
            html_content=html_content,
            recipients=recipients,
            scheduled_at=scheduled_at.strftime("%Y-%m-%d %H:%M:%S") if scheduled_at else None
        )
        
        try:
            api_response = self.campaigns_api.create_email_campaign(email_campaign)
            logger.info(f"[OK] Campagne creee avec succes: {api_response.id}")
            return {
                'id': api_response.id,
                'name': name,
                'subject': subject,
                'status': 'created',
                'scheduled_at': scheduled_at.isoformat() if scheduled_at else None
            }
        except ApiException as e:
            error_msg = f"Erreur lors de la création de la campagne: {e.status} - {e.reason}"
            if hasattr(e, 'body') and e.body:
                try:
                    import json
                    error_body = json.loads(e.body)
                    if 'message' in error_body:
                        error_msg += f" - {error_body['message']}"
                except:
                    error_msg += f" - {e.body}"
            logger.error(f"[ERROR] {error_msg}")
            raise Exception(error_msg) from e
    
    def send_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Envoie une campagne existante.
        
        Args:
            campaign_id: ID de la campagne à envoyer
        
        Returns:
            Dict contenant le statut de l'envoi
        """
        try:
            api_response = self.campaigns_api.send_email_campaign_now(campaign_id)
            logger.info(f"[OK] Campagne {campaign_id} envoyee avec succes")
            return {
                'campaign_id': campaign_id,
                'status': 'sent',
                'message': 'Campagne envoyée avec succès'
            }
        except ApiException as e:
            error_msg = f"Erreur lors de l'envoi de la campagne {campaign_id}: {e.status} - {e.reason}"
            logger.error(f"[ERROR] {error_msg}")
            raise Exception(error_msg) from e
    
    def get_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Récupère les informations d'une campagne.
        
        Args:
            campaign_id: ID de la campagne
        
        Returns:
            Dict contenant les informations de la campagne
        """
        try:
            api_response = self.campaigns_api.get_email_campaign(campaign_id)
            return {
                'id': api_response.id,
                'name': api_response.name,
                'subject': api_response.subject,
                'type': api_response.type,
                'status': api_response.status,
                'scheduled_at': api_response.scheduled_at,
                'sent_at': api_response.sent_at,
                'recipients': api_response.recipients
            }
        except ApiException as e:
            error_msg = f"Erreur lors de la récupération de la campagne {campaign_id}: {e.status} - {e.reason}"
            logger.error(f"[ERROR] {error_msg}")
            raise Exception(error_msg) from e
    
    def list_campaigns(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Liste les campagnes existantes.
        
        Args:
            limit: Nombre de campagnes à récupérer
            offset: Décalage pour la pagination
        
        Returns:
            Liste des campagnes
        """
        try:
            api_response = self.campaigns_api.get_email_campaigns(
                limit=limit,
                offset=offset
            )
            campaigns = []
            for campaign in api_response.campaigns:
                campaigns.append({
                    'id': campaign.id,
                    'name': campaign.name,
                    'subject': campaign.subject,
                    'type': campaign.type,
                    'status': campaign.status,
                    'scheduled_at': campaign.scheduled_at,
                    'sent_at': campaign.sent_at
                })
            return campaigns
        except ApiException as e:
            error_msg = f"Erreur lors de la récupération des campagnes: {e.status} - {e.reason}"
            logger.error(f"[ERROR] {error_msg}")
            raise Exception(error_msg) from e
    
    def update_campaign(
        self,
        campaign_id: int,
        name: Optional[str] = None,
        subject: Optional[str] = None,
        html_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Met à jour une campagne existante.
        
        Args:
            campaign_id: ID de la campagne à mettre à jour
            name: Nouveau nom (optionnel)
            subject: Nouveau sujet (optionnel)
            html_content: Nouveau contenu HTML (optionnel)
        
        Returns:
            Dict contenant les informations mises à jour
        """
        try:
            update_campaign = sib_api_v3_sdk.UpdateEmailCampaign()
            if name:
                update_campaign.name = name
            if subject:
                update_campaign.subject = subject
            if html_content:
                update_campaign.html_content = html_content
            
            api_response = self.campaigns_api.update_email_campaign(campaign_id, update_campaign)
            logger.info(f"[OK] Campagne {campaign_id} mise a jour avec succes")
            return {
                'campaign_id': campaign_id,
                'status': 'updated'
            }
        except ApiException as e:
            error_msg = f"Erreur lors de la mise à jour de la campagne {campaign_id}: {e.status} - {e.reason}"
            logger.error(f"[ERROR] {error_msg}")
            raise Exception(error_msg) from e
    
    def delete_campaign(self, campaign_id: int) -> bool:
        """
        Supprime une campagne.
        
        Args:
            campaign_id: ID de la campagne à supprimer
        
        Returns:
            True si la suppression a réussi
        """
        try:
            self.campaigns_api.delete_email_campaign(campaign_id)
            logger.info(f"[OK] Campagne {campaign_id} supprimee avec succes")
            return True
        except ApiException as e:
            error_msg = f"Erreur lors de la suppression de la campagne {campaign_id}: {e.status} - {e.reason}"
            logger.error(f"[ERROR] {error_msg}")
            raise Exception(error_msg) from e
    
    def create_and_send_campaign(
        self,
        name: str,
        subject: str,
        html_content: str,
        sender_name: str = None,
        sender_email: str = None,
        list_ids: List[int] = None
    ) -> Dict[str, Any]:
        """
        Crée et envoie immédiatement une campagne.
        
        Args:
            name: Nom de la campagne
            subject: Sujet de l'email
            html_content: Contenu HTML de l'email
            sender_name: Nom de l'expéditeur
            sender_email: Email de l'expéditeur
            list_ids: Liste des IDs de listes de contacts
        
        Returns:
            Dict contenant les informations de la campagne créée et envoyée
        """
        # Créer la campagne
        campaign = self.create_campaign(
            name=name,
            subject=subject,
            html_content=html_content,
            sender_name=sender_name,
            sender_email=sender_email,
            list_ids=list_ids,
            scheduled_at=None  # Envoi immédiat
        )
        
        # Envoyer la campagne
        send_result = self.send_campaign(campaign['id'])
        
        return {
            **campaign,
            **send_result
        }

