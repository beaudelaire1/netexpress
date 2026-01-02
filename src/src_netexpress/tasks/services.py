from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationRow:
    label: str
    value: str


class EmailNotificationService:
    """Service d'envoi d'e-mails PREMIUM (HTML uniquement).

    - jamais bloquant
    - jamais crashant
    - log les erreurs en production
    """

    @classmethod
    def send_with_template(
        cls,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        attachments: Optional[List[tuple[str, bytes]]] = None,
    ) -> None:
        """Send an email using a Django template, preferring Brevo API.
        
        Parameters
        ----------
        to_email : str
            Recipient email address
        subject : str
            Email subject
        template_name : str
            Django template path (e.g., "emails/task_assignment.html")
        context : dict
            Template context
        attachments : list of tuple, optional
            List of (filename, content_bytes) tuples
        """
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        # Try to use Brevo with Django template if configured
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
                        return
            except Exception as exc:
                logger.error(
                    "Failed to send email via Brevo (falling back to SMTP): %s | to=%s | subject=%s",
                    exc,
                    to_email,
                    subject,
                )
        
        # Fallback: use Django mail
        html_body = render_to_string(template_name, context)
        text_body = strip_tags(html_body)
        
        # Use the generic send logic
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
        
        email = EmailMessage(
            subject=subject,
            body=html_body,
            from_email=from_email,
            to=[to_email],
        )
        email.content_subtype = "html"
        
        # Add attachments if provided
        if attachments:
            for filename, content in attachments:
                email.attach(filename, content)
        
        try:
            email.send()
        except Exception as exc:
            logger.error(
                "EmailNotificationService.send_with_template FAILED (ignored): %s | to=%s | subject=%s",
                exc,
                to_email,
                subject,
            )

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
    ) -> None:
        brand = getattr(settings, "INVOICE_BRANDING", {}).get("name", "Nettoyage Express")

        html = render_to_string(
            "emails/notification_generic.html",
            {
                "brand": brand.upper(),
                "headline": headline,
                "intro": intro,
                "rows": rows or [],
                "action_url": action_url,
                "action_label": action_label,
            },
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

        email = EmailMessage(
            subject=subject,
            body=html,
            from_email=from_email,
            to=[to],
        )
        email.content_subtype = "html"

        try:
            email.send()  # ⚠️ PAS fail_silently
        except Exception as exc:
            logger.error(
                "EmailNotificationService.send FAILED (ignored): %s | to=%s | subject=%s",
                exc,
                to,
                subject,
            )
