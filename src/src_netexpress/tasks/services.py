from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationRow:
    label: str
    value: str


def get_task_notification_recipient() -> Optional[str]:
    """Retourne le destinataire explicite des notifications internes de tâches."""
    recipient = (getattr(settings, "TASK_NOTIFICATION_EMAIL", "") or "").strip()
    return recipient or None


class EmailNotificationService:
    """Service d'envoi d'e-mails HTML non bloquant et observable."""

    @classmethod
    def send_with_template(
        cls,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        attachments: Optional[List[Tuple[str, bytes]]] = None,
    ) -> bool:
        """Envoie un e-mail à partir d'un template Django.

        Brevo API est utilisé lorsqu'il est explicitement configuré. En cas
        d'échec, le backend e-mail Django sert de repli. La méthode ne propage
        pas les erreurs de transport : elle les journalise et retourne False.
        """
        try:
            if getattr(settings, "EMAIL_BACKEND", "").endswith("BrevoEmailBackend"):
                try:
                    from core.services.brevo_email_service import BrevoEmailService

                    brevo = BrevoEmailService()
                    if brevo.api_instance:
                        sent = brevo.send_with_django_template(
                            to_email=to_email,
                            subject=subject,
                            template_name=template_name,
                            context=context,
                            attachments=attachments,
                        )
                        if sent:
                            return True
                        logger.warning(
                            "Brevo API returned an unsuccessful result; falling back to Django email | to=%s | subject=%s",
                            to_email,
                            subject,
                        )
                except Exception:
                    logger.exception(
                        "Brevo API notification failed; falling back to Django email | to=%s | subject=%s",
                        to_email,
                        subject,
                    )

            html_body = render_to_string(template_name, context)
            # Render the text version as a sanity check for malformed template output
            # and to keep behaviour aligned with the other notification service.
            strip_tags(html_body)

            email = EmailMessage(
                subject=subject,
                body=html_body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
                to=[to_email],
            )
            email.content_subtype = "html"

            for filename, content in attachments or []:
                email.attach(filename, content)

            sent_count = email.send(fail_silently=False)
            if sent_count < 1:
                logger.error(
                    "Notification email backend accepted no message | to=%s | subject=%s",
                    to_email,
                    subject,
                )
                return False
            return True
        except Exception:
            logger.exception(
                "EmailNotificationService.send_with_template failed | to=%s | subject=%s",
                to_email,
                subject,
            )
            return False

    @staticmethod
    def send(
        *,
        to: str,
        subject: str,
        headline: str,
        intro: str,
        rows: Optional[List[Dict[str, str]]] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
    ) -> bool:
        """Envoie une notification générique et retourne son état réel."""
        try:
            html = render_to_string(
                "emails/notification_generic.html",
                {
                    "brand": getattr(settings, "INVOICE_BRANDING", {}).get(
                        "name", "Nettoyage Express"
                    ).upper(),
                    "headline": headline,
                    "intro": intro,
                    "rows": rows or [],
                    "action_url": action_url,
                    "action_label": action_label,
                },
            )

            email = EmailMessage(
                subject=subject,
                body=html,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
                to=[to],
            )
            email.content_subtype = "html"

            sent_count = email.send(fail_silently=False)
            if sent_count < 1:
                logger.error(
                    "Notification email backend accepted no message | to=%s | subject=%s",
                    to,
                    subject,
                )
                return False
            return True
        except Exception:
            logger.exception(
                "EmailNotificationService.send failed | to=%s | subject=%s",
                to,
                subject,
            )
            return False
