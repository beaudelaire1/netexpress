from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_quote_email(quote) -> None:
    """Envoie le devis au client avec PDF premium joint.

    Cette fonction est une API simple (utilisable depuis admin/vues).
    Le PDF est généré via ``quote.generate_pdf`` (WeasyPrint).
    """
    if not getattr(quote, "client", None) or not getattr(quote.client, "email", None):
        return

    # Génère/attache le PDF
    quote.generate_pdf(attach=True)

    subject = f"Votre devis {quote.number}"
    ctx = {"quote": quote, "branding": getattr(settings, "INVOICE_BRANDING", {}) or {}}

    text = render_to_string("emails/quote.txt", ctx) if _template_exists("emails/quote.txt") else f"Votre devis {quote.number} est en pièce jointe."
    html = render_to_string("emails/new_quote_pdf.html", ctx)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[quote.client.email],
    )
    email.attach_alternative(html, "text/html")

    # Join PDF from file
    try:
        email.attach_file(quote.pdf.path, mimetype="application/pdf")
    except Exception:
        # fallback: regenerate bytes and attach
        pdf_bytes = quote.generate_pdf(attach=False)
        email.attach(f"{quote.number}.pdf", pdf_bytes, "application/pdf")

    # optional admin copy
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
