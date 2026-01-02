"""
Service d'envoi d'e-mails via l'API Brevo (ex-Sendinblue).

Ce service utilise l'API REST de Brevo qui est plus fiable que SMTP
sur les environnements cloud comme Render.com. Il supporte :
- Envoi d'e-mails HTML et texte
- Pièces jointes (PDFs, images, etc.)
- Tracking et statistiques côté Brevo
"""

from __future__ import annotations

import base64
import logging
from typing import List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """Service d'envoi d'e-mails via l'API Brevo."""

    def __init__(self):
        self.api_key = getattr(settings, "BREVO_API_KEY", None)
        if not self.api_key:
            raise RuntimeError(
                "BREVO_API_KEY n'est pas configuré. "
                "Ajoutez cette variable d'environnement."
            )

    def _get_api_instance(self):
        """Initialise l'instance API Brevo."""
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
        except ImportError:
            raise RuntimeError(
                "Le SDK Brevo n'est pas installé. "
                "Exécutez: pip install sib-api-v3-sdk"
            )

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = self.api_key
        return sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        *,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        attachments: Optional[List[Tuple[str, bytes]]] = None,
        reply_to: Optional[str] = None,
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
            Corps du message en texte brut
        html_body : str, optional
            Corps du message en HTML
        from_email : str, optional
            Adresse de l'expéditeur (défaut: DEFAULT_FROM_EMAIL)
        from_name : str, optional
            Nom de l'expéditeur (défaut: INVOICE_BRANDING["name"])
        attachments : list of tuple(str, bytes), optional
            Liste de pièces jointes [(nom_fichier, contenu_bytes), ...]
        reply_to : str, optional
            Adresse de réponse

        Returns
        -------
        bool
            True si l'envoi a réussi, False sinon
        """
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
        except ImportError:
            logger.error("SDK Brevo non installé")
            return False

        api_instance = self._get_api_instance()

        # Configuration de l'expéditeur
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        sender_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None) or branding.get("email")
        sender_name = from_name or branding.get("name", "NetExpress")

        if not sender_email:
            logger.error("Aucune adresse d'expéditeur configurée")
            return False

        # Construction de l'e-mail
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": sender_email, "name": sender_name},
            subject=subject,
            text_content=body,
        )

        # Ajout du contenu HTML si fourni
        if html_body:
            send_smtp_email.html_content = html_body

        # Ajout de l'adresse de réponse si fournie
        if reply_to:
            send_smtp_email.reply_to = {"email": reply_to}

        # Ajout des pièces jointes
        if attachments:
            attachment_list = []
            for filename, content in attachments:
                # Brevo attend le contenu en base64
                b64_content = base64.b64encode(content).decode("utf-8")
                attachment_list.append({
                    "name": filename,
                    "content": b64_content,
                })
            send_smtp_email.attachment = attachment_list

        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info(f"E-mail envoyé avec succès à {to_email}. Message ID: {api_response.message_id}")
            return True
        except ApiException as e:
            logger.error(f"Erreur Brevo lors de l'envoi à {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'envoi à {to_email}: {e}")
            return False

    def send_with_template(
        self,
        to_email: str,
        template_id: int,
        params: Optional[dict] = None,
        *,
        attachments: Optional[List[Tuple[str, bytes]]] = None,
    ) -> bool:
        """
        Envoie un e-mail en utilisant un template Brevo.

        Parameters
        ----------
        to_email : str
            Adresse e-mail du destinataire
        template_id : int
            ID du template Brevo
        params : dict, optional
            Paramètres dynamiques pour le template
        attachments : list of tuple(str, bytes), optional
            Liste de pièces jointes

        Returns
        -------
        bool
            True si l'envoi a réussi
        """
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
        except ImportError:
            logger.error("SDK Brevo non installé")
            return False

        api_instance = self._get_api_instance()

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            template_id=template_id,
            params=params or {},
        )

        if attachments:
            attachment_list = []
            for filename, content in attachments:
                b64_content = base64.b64encode(content).decode("utf-8")
                attachment_list.append({
                    "name": filename,
                    "content": b64_content,
                })
            send_smtp_email.attachment = attachment_list

        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info(f"E-mail template envoyé à {to_email}. Message ID: {api_response.message_id}")
            return True
        except ApiException as e:
            logger.error(f"Erreur Brevo (template) pour {to_email}: {e}")
            return False
