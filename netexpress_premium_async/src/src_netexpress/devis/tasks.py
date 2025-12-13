"""
Celery tasks for devis (quote) emails.

- Envoi asynchrone d'un devis au client en HTML brandé + PDF en pièce jointe.
"""

from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from core.services.pdf_generator import render_quote_pdf


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_quote_pdf_email(self, quote_id: int) -> None:
    from devis.models import Quote  # local import

    quote = Quote.objects.select_related("client").prefetch_related("quote_items").get(pk=quote_id)

    # Ensure totals + PDF
    try:
        quote.compute_totals()
    except Exception:
        pass

    pdf_res = render_quote_pdf(quote)

    # Build email html
    context = {
        "quote": quote,
        "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
        "cta_url": getattr(settings, "SITE_URL", "").rstrip("/") + f"/devis/{quote.pk}/" if getattr(settings, "SITE_URL", None) else None,
    }
    html = render_to_string("emails/new_quote_pdf.html", context)

    to_email = getattr(quote.client, "email", None) or getattr(quote, "email", None)
    if not to_email:
        return

    subject = f"Votre devis {quote.number}"
    email = EmailMessage(
        subject=subject,
        body=html,
        to=[to_email],
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
    )
    email.content_subtype = "html"
    email.attach(pdf_res.filename, pdf_res.content, "application/pdf")

    # Optional admin copy
    admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
    if admin_email:
        email.bcc = [admin_email]

    email.send(fail_silently=False)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_quote_request_received(self, quote_request_id: int) -> None:
    from devis.models import QuoteRequest
    qr = QuoteRequest.objects.get(pk=quote_request_id)
    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    context = {
        "quote_request": qr,
        "branding": branding,
        "cta_url": getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/") + "/devis/demande/",
    }
    html = render_to_string("emails/new_quote.html", context)

    if not qr.email:
        return
    email = EmailMessage(
        subject="Votre demande de devis a bien été reçue",
        body=html,
        to=[qr.email],
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
    )
    email.content_subtype = "html"
    # optional admin notification
    admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
    if admin_email:
        email.bcc = [admin_email]
    email.send(fail_silently=False)
