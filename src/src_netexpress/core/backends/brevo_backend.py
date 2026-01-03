"""
Backend email personnalisé pour Brevo (ex-Sendinblue) avec fallback console robuste
"""
import logging
import hashlib
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)

def _key_fingerprint(key: str) -> str:
    if not key:
        return "none"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return h[:10]


class BrevoEmailBackend(BaseEmailBackend):
    """
    Backend email utilisant l'API Brevo pour l'envoi d'emails transactionnels.
    Avec fallback automatique vers console en cas d'erreur en développement.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        
        # Configuration de l'API Brevo
        self.api_key = getattr(settings, 'BREVO_API_KEY', None)
        self.api_instance = None
        self.console_backend = None
        self.use_fallback = False
        # Controle explicitement si on autorise le fallback console
        # (utile pour eviter "ca marche mais ca imprime en console" quand on veut forcer l'envoi reel)
        self.allow_console_fallback = getattr(settings, "BREVO_CONSOLE_FALLBACK", getattr(settings, "DEBUG", False))
        
        # Vérifier si on est en mode développement
        self.is_development = getattr(settings, 'DEBUG', False)
        
        # Initialiser le backend console pour fallback
        self.console_backend = ConsoleEmailBackend(fail_silently=self.fail_silently)
        
        if not self.api_key or self.api_key.strip() == '' or 'your-brevo-api-key-here' in self.api_key:
            if self.allow_console_fallback:
                logger.warning("[FALLBACK] Cle API Brevo non configuree, utilisation du fallback console")
                self.use_fallback = True
            else:
                raise ImproperlyConfigured("BREVO_API_KEY manquante et BREVO_CONSOLE_FALLBACK=False")
        else:
            try:
                # Configuration du client API
                configuration = sib_api_v3_sdk.Configuration()
                api_key_str = str(self.api_key).strip()
                configuration.api_key['api-key'] = api_key_str
                self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
                logger.info(f"[OK] Backend Brevo initialise (key_fingerprint={_key_fingerprint(api_key_str)})")
            except Exception as e:
                logger.error(f"[ERROR] Erreur lors de l'initialisation Brevo: {e}")
                if self.is_development and self.allow_console_fallback:
                    logger.info("[FALLBACK] Mode developpement: fallback vers console active")
                    self.use_fallback = True
                elif not self.fail_silently:
                    raise
    
    def send_messages(self, email_messages):
        """
        Envoie une liste de messages email via l'API Brevo ou console en fallback.
        """
        # Si fallback activé ou pas d'API configurée, utiliser console
        if self.use_fallback or not self.api_instance:
            if self.allow_console_fallback:
                logger.info("[FALLBACK] Envoi via console (fallback)")
                return self.console_backend.send_messages(email_messages)
            raise ImproperlyConfigured("BrevoEmailBackend en mode fallback console interdit (BREVO_CONSOLE_FALLBACK=False)")
        
        # Essayer d'envoyer via Brevo
        try:
            num_sent = 0
            for message in email_messages:
                if self._send_message_brevo(message):
                    num_sent += 1
                else:
                    # En cas d'échec, essayer console en développement
                    if self.is_development and self.allow_console_fallback:
                        logger.warning("[FALLBACK] Echec Brevo, fallback vers console pour ce message")
                        self.console_backend.send_messages([message])
                    elif not self.fail_silently:
                        raise Exception("Echec envoi Brevo (fallback console desactive)")
            return num_sent
        except Exception as e:
            logger.error(f"[ERROR] Erreur generale Brevo: {e}")
            if self.is_development and self.allow_console_fallback:
                logger.info("[FALLBACK] Fallback complet vers console")
                return self.console_backend.send_messages(email_messages)
            elif not self.fail_silently:
                raise
            return 0
    
    def _send_message_brevo(self, message):
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
                logger.warning("[WARN] Aucun destinataire valide trouve")
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
            logger.info(f"[OK] Email envoye via Brevo: {api_response.message_id}")
            return True
            
        except ApiException as e:
            error_msg = f"Erreur API Brevo (status {e.status}): {e.reason}"
            if hasattr(e, 'body') and e.body:
                try:
                    import json
                    error_body = json.loads(e.body)
                    if 'message' in error_body:
                        error_msg += f" - {error_body['message']}"
                except:
                    error_msg += f" - {e.body}"
            
            logger.error(error_msg)
            
            # Pour les erreurs d'authentification (401), suggérer de vérifier la clé API
            if e.status == 401:
                key_fp = _key_fingerprint(str(getattr(settings, 'BREVO_API_KEY', '') or '').strip())
                logger.error(
                    "[ERROR] 401 Unauthorized - Key not found. "
                    f"Verifie BREVO_API_KEY (fingerprint={key_fp}) et le settings module utilise."
                )
                # En développement, activer le fallback permanent
                if self.is_development and self.allow_console_fallback:
                    logger.info("[FALLBACK] Activation du fallback permanent en developpement")
                    self.use_fallback = True
            
            if not self.fail_silently:
                # En développement, ne pas lever d'exception, utiliser fallback
                if self.is_development and self.allow_console_fallback:
                    logger.warning("[FALLBACK] Utilisation du fallback console pour ce message")
                    return False  # Sera géré par le fallback dans send_messages
                else:
                    raise Exception(f"Erreur lors de l'envoi de l'email via Brevo: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Erreur lors de l'envoi email: {e}", exc_info=True)
            if not self.fail_silently:
                if self.is_development and self.allow_console_fallback:
                    return False  # Fallback sera utilisé
                else:
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
        
        # Si content_subtype est 'html', le body EST déjà du HTML - l'utiliser tel quel
        if hasattr(message, 'content_subtype') and message.content_subtype == 'html':
            return message.body
        
        # Si le body est déjà du HTML complet (contient <!DOCTYPE ou <html), l'utiliser tel quel
        if message.body:
            body_lower = message.body.lower().strip()
            if body_lower.startswith('<!doctype') or body_lower.startswith('<html'):
                return message.body
            
            # Si le body contient des balises HTML, l'utiliser tel quel
            if '<' in message.body and '>' in message.body:
                return message.body
            
            # Texte brut : conversion simple
            return message.body.replace('\n', '<br>')
            
        return None