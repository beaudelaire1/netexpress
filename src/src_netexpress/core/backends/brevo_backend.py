"""
Backend email personnalisé pour Brevo (ex-Sendinblue)
"""
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    """
    Backend email utilisant l'API Brevo pour l'envoi d'emails transactionnels.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        
        # Configuration de l'API Brevo
        self.api_key = getattr(settings, 'BREVO_API_KEY', None)
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError("BREVO_API_KEY must be set in settings")
            return
            
        # Configuration du client API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = self.api_key
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    def send_messages(self, email_messages):
        """
        Envoie une liste de messages email via l'API Brevo.
        """
        if not self.api_key:
            return 0
            
        num_sent = 0
        for message in email_messages:
            if self._send_message(message):
                num_sent += 1
        return num_sent
    
    def _send_message(self, message):
        """
        Envoie un message email individuel via l'API Brevo.
        """
        try:
            # Préparer les destinataires
            to_list = []
            for email in message.to:
                if '@' in email:
                    to_list.append({"email": email})
                    
            if not to_list:
                logger.warning("Aucun destinataire valide trouvé")
                return False
            
            # Préparer l'expéditeur
            sender_email = message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
            sender_name = getattr(settings, 'DEFAULT_FROM_NAME', 'Nettoyage Express')
            
            # Créer l'objet email transactionnel
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to_list,
                sender={"name": sender_name, "email": sender_email},
                subject=message.subject,
                html_content=self._get_html_content(message),
                text_content=message.body if message.body else None,
            )
            
            # Ajouter les pièces jointes si présentes
            if hasattr(message, 'attachments') and message.attachments:
                attachments = []
                for attachment in message.attachments:
                    if hasattr(attachment, 'read'):  # File-like object
                        content = attachment.read()
                        if hasattr(attachment, 'name'):
                            name = attachment.name
                        else:
                            name = 'attachment'
                    else:  # Tuple (filename, content, mimetype)
                        name, content, mimetype = attachment
                    
                    # Encoder en base64
                    import base64
                    content_b64 = base64.b64encode(content).decode('utf-8')
                    attachments.append({
                        "name": name,
                        "content": content_b64
                    })
                
                if attachments:
                    send_smtp_email.attachment = attachments
            
            # Envoyer l'email
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email envoyé via Brevo: {api_response.message_id}")
            return True
            
        except ApiException as e:
            logger.error(f"Erreur API Brevo: {e}")
            if not self.fail_silently:
                raise
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi email: {e}")
            if not self.fail_silently:
                raise
            return False
    
    def _get_html_content(self, message):
        """
        Récupère le contenu HTML du message.
        """
        # Si le message a des alternatives (HTML), les utiliser
        if hasattr(message, 'alternatives') and message.alternatives:
            for content, mimetype in message.alternatives:
                if mimetype == 'text/html':
                    return content
        
        # Sinon, utiliser le body comme HTML si il contient des balises
        if message.body and ('<' in message.body and '>' in message.body):
            return message.body
            
        # Convertir le texte brut en HTML simple
        if message.body:
            return message.body.replace('\n', '<br>')
            
        return None