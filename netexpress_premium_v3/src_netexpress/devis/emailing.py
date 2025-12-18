"""devis/emailing.py

Envoi d'emails "transactionnels" pour l'app devis.

Objectifs
---------
- Ne dépend PAS de Celery pour fonctionner en dev/prod.
- Garantit la génération du PDF AVANT l'envoi.
- Utilise les templates premium (emails/new_quote_pdf.html).
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.services.pdf_generator import render_quote_pdf


def _site_url() -> str:
    return (getattr(settings, "SITE_URL", "") or "").rstrip("/")


def ensure_quote_pdf(quote) -> None:
    """Génère et attache le PDF au devis si absent."""
    if getattr(quote, "pdf", None):
        # Champ FileField : truthy si fichier associé
        try:
            if quote.pdf and quote.pdf.name:
                return
        except Exception:
            pass

    pdf_res = render_quote_pdf(quote)
    quote.pdf.save(pdf_res.filename, ContentFile(pdf_res.content), save=True)


def send_quote_pdf_email(quote) -> None:
    """Envoie un email premium au client avec le PDF en pièce jointe."""
    # Totaux à jour (best-effort)
    try:
        if hasattr(quote, "compute_totals"):
            quote.compute_totals()
            quote.refresh_from_db(fields=["total_ht", "tva", "total_ttc"])
    except Exception:
        pass

    ensure_quote_pdf(quote)

    to_email = getattr(getattr(quote, "client", None), "email", None) or getattr(quote, "email", None)
    if not to_email:
        return

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    context = {
        "quote": quote,
        "branding": branding,
        "cta_url": f"{_site_url()}/devis/{quote.pk}/" if _site_url() else None,
    }

    subject = f"Votre devis {getattr(quote, 'number', quote.pk)}"
    text_body = render_to_string("emails/new_quote_pdf.txt", context) if _template_exists("emails/new_quote_pdf.txt") else "Veuillez trouver votre devis en pièce jointe."
    html_body = render_to_string("emails/new_quote_pdf.html", context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
    )
    email.attach_alternative(html_body, "text/html")

    # joindre depuis le fichier sauvegardé (plus fiable)
    try:
        email.attach_file(quote.pdf.path, mimetype="application/pdf")
    except Exception:
        # fallback : jointe en mémoire
        pdf_res = render_quote_pdf(quote)
        email.attach(pdf_res.filename, pdf_res.content, "application/pdf")

    # Copie admin (BCC)
    admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
    if admin_email:
        email.bcc = [admin_email]

    email.send(fail_silently=False)


def _template_exists(template_name: str) -> bool:
    from django.template import engines
    try:
        engines["django"].get_template(template_name)
        return True
    except Exception:
        return False
