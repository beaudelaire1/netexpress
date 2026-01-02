"""
Service d'envoi d'e-mails via l'API Brevo (ex-Sendinblue) avec support des templates Django.

Ce service permet d'envoyer des e-mails transactionnels via l'API Brevo
en utilisant les templates Django existants pour le rendu HTML.
"""

import logging
import base64
from typing import Optional, List, Tuple

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """Service d'envoi d'e-mails via l'API Brevo avec support des templates Django."""
    
    def __init__(self):
        """Initialise le service avec la configuration Brevo."""
        self.api_key = getattr(settings, 'BREVO_API_KEY', None)
        self.api_instance = None
        self.sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
        self.sender_name = getattr(settings, 'DEFAULT_FROM_NAME', 'Nettoyage Express')
        
        if not self.api_key or self.api_key.strip() == '':
            logger.warning("BREVO_API_KEY not configured")
            return
        
        try:
            # Configuration du client API
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = str(self.api_key).strip()
            self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
            logger.info("BrevoEmailService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Brevo API: {e}")
            self.api_instance = None
    
    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        *,
        html_body: Optional[str] = None,
        attachments: Optional[List[Tuple[str, bytes]]] = None,
    ) -> bool:
        """
        Envoie un e-mail via l'API Brevo.
        
        Parameters
        ----------
        to_email : str
            Adresse e-mail du destinataire
        subject : str
            Sujet de l'e-mail
        body : str
            Contenu texte de l'e-mail
        html_body : str, optional
            Contenu HTML de l'e-mail
        attachments : list of tuple, optional
            Liste de tuples (nom_fichier, contenu_bytes)
        
        Returns
        -------
        bool
            True si l'envoi a réussi, False sinon
        """
        if not self.api_instance:
            logger.error("Brevo API not initialized")
            return False
        
        try:
            # Préparer les destinataires
            to_list = [{"email": to_email}]
            
            # Créer l'objet email transactionnel
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to_list,
                sender={"name": self.sender_name, "email": self.sender_email},
                subject=subject,
                html_content=html_body if html_body else body.replace('\n', '<br>'),
                text_content=body,
            )
            
            # Ajouter les pièces jointes si présentes
            if attachments:
                attachment_list = []
                for filename, content in attachments:
                    # Encoder en base64
                    content_b64 = base64.b64encode(content).decode('utf-8')
                    attachment_list.append({
                        "name": filename,
                        "content": content_b64
                    })
                send_smtp_email.attachment = attachment_list
            
            # Envoyer l'email
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email sent via Brevo: {api_response.message_id}")
            return True
            
        except ApiException as e:
            logger.error(f"Brevo API error (status {e.status}): {e.reason}")
            if hasattr(e, 'body') and e.body:
                try:
                    import json
                    error_body = json.loads(e.body)
                    if 'message' in error_body:
                        logger.error(f"Brevo error message: {error_body['message']}")
                except:
                    pass
            return False
        except Exception as e:
            logger.error(f"Failed to send email via Brevo: {e}", exc_info=True)
            return False
    
    def send_with_django_template(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        *,
        attachments: Optional[List[Tuple[str, bytes]]] = None,
    ) -> bool:
        """
        Envoie un e-mail en utilisant un template Django.
        
        Cette méthode rend le template HTML avec Django, puis envoie
        l'e-mail via l'API Brevo avec le HTML généré.
        
        Parameters
        ----------
        to_email : str
            Adresse e-mail du destinataire
        subject : str
            Sujet de l'e-mail
        template_name : str
            Chemin du template (ex: "emails/invoice_notification.html")
        context : dict
            Contexte pour le rendu du template
        attachments : list of tuple, optional
            Liste de tuples (nom_fichier, contenu_bytes)
        
        Returns
        -------
        bool
            True si l'envoi a réussi, False sinon
        """
        try:
            # Rendre le template HTML avec Django
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
            
            return self.send(
                to_email=to_email,
                subject=subject,
                body=text_content,
                html_body=html_content,
                attachments=attachments,
            )
        except Exception as e:
            logger.error(f"Failed to render template '{template_name}': {e}", exc_info=True)
            return False
