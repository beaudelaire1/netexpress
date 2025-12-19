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
