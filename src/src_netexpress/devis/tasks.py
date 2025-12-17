"""
Celery tasks for devis (quote) emails.

- Envoi asynchrone d'un devis au client en HTML brandé + PDF en pièce jointe.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from core.services.pdf_generator import render_quote_pdf

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes entre les retries
    max_retries=5,
    acks_late=True,  # Acknowledge seulement après succès
)
def send_quote_pdf_email(self, quote_id: int) -> Dict[str, Any]:
    """Envoi asynchrone du devis PDF au client.

    Retourne un dictionnaire avec le statut de l'opération.
    """
    from devis.models import Quote

    logger.info("Démarrage envoi email devis ID=%s (tentative %s/%s)",
                quote_id, self.request.retries + 1, self.max_retries + 1)

    # Récupération du devis
    try:
        quote = Quote.objects.select_related("client").prefetch_related("quote_items").get(pk=quote_id)
    except Quote.DoesNotExist:
        logger.error("Devis ID=%s introuvable, abandon de la tâche", quote_id)
        return {"status": "error", "reason": "quote_not_found", "quote_id": quote_id}

    # Calcul des totaux
    try:
        quote.compute_totals()
        logger.debug("Totaux calculés pour devis %s: HT=%s TTC=%s",
                    quote.number, quote.total_ht, quote.total_ttc)
    except Exception as e:
        logger.warning("compute_totals échoué pour devis %s: %s", quote.number, e)
        # On continue quand même

    # Génération du PDF
    try:
        pdf_res = render_quote_pdf(quote)
        logger.debug("PDF généré pour devis %s: %s (%d bytes)",
                    quote.number, pdf_res.filename, len(pdf_res.content))
    except Exception as e:
        logger.exception("Génération PDF échouée pour devis %s", quote.number)
        raise  # Retry automatique

    # Validation du destinataire
    to_email = getattr(quote.client, "email", None) or getattr(quote, "email", None)
    if not to_email:
        logger.warning("Pas d'email client pour devis %s, envoi ignoré", quote.number)
        return {"status": "skipped", "reason": "no_recipient", "quote": quote.number}

    # Construction de l'email
    site_url = getattr(settings, "SITE_URL", None)
    cta_url = f"{site_url.rstrip('/')}/devis/{quote.pk}/" if site_url else None

    context = {
        "quote": quote,
        "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
        "cta_url": cta_url,
    }
    html = render_to_string("emails/new_quote_pdf.html", context)

    email = EmailMessage(
        subject=f"Votre devis {quote.number}",
        body=html,
        to=[to_email],
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
    )
    email.content_subtype = "html"
    email.attach(pdf_res.filename, pdf_res.content, "application/pdf")

    # Copie admin en BCC
    admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
    if admin_email:
        email.bcc = [admin_email]
        logger.debug("Admin en copie: %s", admin_email)

    # Envoi
    try:
        email.send(fail_silently=False)
        logger.info("Email devis %s envoyé avec succès à %s", quote.number, to_email)
        return {
            "status": "sent",
            "quote": quote.number,
            "to": to_email,
            "pdf_size": len(pdf_res.content),
        }
    except Exception as e:
        logger.exception("Envoi email échoué pour devis %s vers %s", quote.number, to_email)
        raise  # Retry automatique


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
    acks_late=True,
)
def send_quote_request_received(self, quote_request_id: int) -> Dict[str, Any]:
    """Notification de réception de demande de devis au client."""
    from devis.models import QuoteRequest

    logger.info("Envoi confirmation demande devis ID=%s (tentative %s/%s)",
                quote_request_id, self.request.retries + 1, self.max_retries + 1)

    try:
        qr = QuoteRequest.objects.get(pk=quote_request_id)
    except QuoteRequest.DoesNotExist:
        logger.error("QuoteRequest ID=%s introuvable", quote_request_id)
        return {"status": "error", "reason": "quote_request_not_found"}

    if not qr.email:
        logger.warning("Pas d'email pour QuoteRequest ID=%s", quote_request_id)
        return {"status": "skipped", "reason": "no_recipient"}

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    site_url = getattr(settings, "SITE_URL", "http://localhost:8000")

    context = {
        "quote_request": qr,
        "branding": branding,
        "cta_url": site_url.rstrip("/") + "/devis/demande/",
    }
    html = render_to_string("emails/new_quote.html", context)

    email = EmailMessage(
        subject="Votre demande de devis a bien été reçue",
        body=html,
        to=[qr.email],
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
    )
    email.content_subtype = "html"

    admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
    if admin_email:
        email.bcc = [admin_email]

    try:
        email.send(fail_silently=False)
        logger.info("Confirmation demande devis envoyée à %s", qr.email)
        return {"status": "sent", "to": qr.email}
    except Exception as e:
        logger.exception("Envoi confirmation échoué pour %s", qr.email)
        raise  # Retry automatique
