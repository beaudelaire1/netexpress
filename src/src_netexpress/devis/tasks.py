"""
Celery tasks for devis (quote) emails.

- Envoi asynchrone d'un devis au client en HTML brandé + PDF en pièce jointe.
"""

from __future__ import annotations

try:
    from celery import shared_task  # type: ignore
except Exception:  # Celery non installé -> fallback
    def shared_task(*dargs, **dkwargs):  # type: ignore
        def _decorator(fn):
            return fn
        return _decorator

import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from core.notifications import send_notification
from core.services.document_generator import DocumentGenerator

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_quote_pdf_email(self, quote_id: int) -> None:
    from devis.models import Quote  # local import

    quote = Quote.objects.select_related("client").prefetch_related("quote_items").get(pk=quote_id)

    # Ensure totals + PDF
    try:
        quote.compute_totals()
    except Exception:
        pass

    # generate_pdf plutôt que generate_quote_pdf : cette pièce jointe ne doit pas
    # réécrire le PDF stocké sur le devis. Même gabarit et même préfixe.
    pdf_res = DocumentGenerator.generate_pdf(quote, "pdf/quote_premium.html", "DEV")

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


def send_quote_request_notification(quote_request_id: int) -> None:
    """Confirme la réception au demandeur puis prévient le gestionnaire."""
    from devis.models import QuoteRequest  # import local : évite un cycle

    try:
        qr = QuoteRequest.objects.get(pk=quote_request_id)
    except QuoteRequest.DoesNotExist:
        logger.warning("Demande de devis %s introuvable : rien à notifier", quote_request_id)
        return

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    site_url = (getattr(settings, "SITE_URL", "") or "http://localhost:8000").rstrip("/")
    reference = f"REQ-{qr.pk:05d}"

    # -------------------------
    # 1) Accusé de réception au demandeur
    # -------------------------
    if qr.email:
        html = render_to_string(
            "emails/new_quote.html",
            {
                "quote_request": qr,
                "branding": branding,
                "cta_url": site_url + "/devis/nouveau/",
            },
        )
        email = EmailMessage(
            subject="Votre demande de devis a bien été reçue",
            body=html,
            to=[qr.email],
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)

    # -------------------------
    # 2) Notification interne
    # -------------------------
    admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
    if not admin_email:
        logger.error(
            "Demande de devis %s enregistrée mais non notifiée : "
            "TASK_NOTIFICATION_EMAIL n'est pas configuré.",
            quote_request_id,
        )
        return

    # Les libellés lisent les champs réels de QuoteRequest : les anciens
    # `topic`, `zip_code` et `city` n'existent pas sur ce modèle et laissaient
    # la moitié du récapitulatif vide.
    rows = [
        {"label": "Type de service", "value": qr.get_service_type_display() or "Non précisé"},
        {"label": "Client", "value": qr.client_name or "—"},
        {"label": "Téléphone", "value": qr.phone or "—"},
        {"label": "Email", "value": qr.email or "—"},
        {"label": "Adresse", "value": qr.address or "—"},
        {"label": "Surface", "value": f"{qr.surface} m²" if qr.surface else "—"},
        {"label": "Délai souhaité", "value": qr.get_deadline_display() or "—"},
    ]
    if qr.preferred_date:
        rows.append({"label": "Date souhaitée", "value": qr.preferred_date.strftime("%d/%m/%Y")})

    html_admin = render_to_string(
        "emails/notification_generic.html",
        {
            "brand": branding.get("name", "NETTOYAGE EXPRESS"),
            "title": "Nouvelle demande de devis",
            "headline": "Nouvelle demande de devis reçue",
            "intro": "Une nouvelle demande a été soumise via le formulaire du site. Voici le récapitulatif.",
            "rows": rows,
            "action_url": site_url + "/admin/devis/quoterequest/",
            "action_label": "Ouvrir dans l'admin",
            "reference": reference,
        },
    )
    em = EmailMessage(
        subject=f"[Nettoyage Express] Nouvelle demande de devis ({reference})",
        body=html_admin,
        to=[admin_email],
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        # Répondre au courriel écrit directement au demandeur.
        reply_to=[qr.email] if qr.email else None,
    )
    em.content_subtype = "html"
    em.send(fail_silently=False)
    logger.info("Notification de demande de devis %s envoyée à %s", reference, admin_email)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_quote_request_received(self, quote_request_id: int) -> None:
    """Variante Celery, utilisée uniquement si NOTIFY_EMAILS_ASYNC est actif."""
    return send_quote_request_notification(quote_request_id)


def notify_new_quote_request(quote_request_id: int) -> bool:
    """Point d'entrée unique de la vue publique. True si la notification est partie."""
    return send_notification(
        f"demande de devis {quote_request_id}",
        send_quote_request_notification,
        args=(quote_request_id,),
        celery_task=send_quote_request_received,
    )
