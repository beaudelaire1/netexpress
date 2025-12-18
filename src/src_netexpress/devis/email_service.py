from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse


def _base_url(request=None) -> str:
    """Return the base URL for absolute links in emails."""
    if request is not None:
        try:
            return request.build_absolute_uri('/').rstrip('/')
        except Exception:
            pass
    return str(getattr(settings, 'SITE_URL', 'http://localhost:8000')).rstrip('/')


def send_quote_email(quote, request=None, *, to_email: Optional[str] = None) -> None:
    """Send the premium quote email with PDF attached.

    Uses templates/emails/modele_quote.html (provided by the user).
    """
    # Ensure totals are up-to-date
    try:
        quote.compute_totals()
    except Exception:
        pass

    # Ensure PDF exists
    if not getattr(quote, 'pdf', None):
        quote.generate_pdf(attach=True)

    base = _base_url(request)
    # Public PDF and validation links require a QuoteValidation token.
    # We create a fresh token each time we send the email.
    from .models import QuoteValidation
    validation = QuoteValidation.create_for_quote(quote)
    pdf_url = f"{base}{reverse('devis:quote_public_pdf', kwargs={'token': quote.public_token})}"
    validation_url = f"{base}{reverse('devis:quote_validate_start', kwargs={'token': validation.token})}"

    client = getattr(quote, 'client', None)
    client_name = getattr(client, 'full_name', '') if client is not None else ''
    recipient = to_email or (getattr(client, 'email', None) if client is not None else None)
    if not recipient:
        return

    subject = f"Votre devis {quote.number} — {getattr(settings, 'INVOICE_BRANDING', {}).get('name', 'Nettoyage Express')}"
    company_name = getattr(settings, 'INVOICE_BRANDING', {}).get('name', 'Nettoyage Express')

    # HTML ONLY: aucune notification en texte (exigence projet)
    html_body = render_to_string(
        'emails/modele_quote.html',
        {
            'quote': quote,
            'client_name': client_name or 'Bonjour',
            'company_name': company_name,
            'pdf_url': pdf_url,
            'validation_url': validation_url,
            'validation_code': validation.code,
        },
    )

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@example.com'
    email = EmailMessage(subject=subject, body=html_body, from_email=from_email, to=[recipient])
    email.content_subtype = 'html'

    # Attach PDF
    try:
        if quote.pdf and hasattr(quote.pdf, 'open'):
            with quote.pdf.open('rb') as f:
                email.attach(f"{quote.number}.pdf", f.read(), 'application/pdf')
    except Exception:
        pass

    email.send(fail_silently=False)


def send_quote_validation_code(quote, validation, request=None, *, to_email: Optional[str] = None) -> None:
    """Send the OTP code email (step 1 of 2FA)."""
    client = getattr(quote, 'client', None)
    recipient = to_email or (getattr(client, 'email', None) if client is not None else None)
    if not recipient:
        return

    base = _base_url(request)
    code_url = f"{base}{reverse('devis:quote_validate_code', kwargs={'token': validation.token})}"

    subject = f"Code de confirmation pour valider le devis {quote.number}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@example.com'

    # Le template générique attend : headline/intro + action_url/action_label
    html = render_to_string(
        'emails/notification_generic.html',
        {
            'headline': 'Validation du devis — Code de confirmation',
            'intro': (
                f"Bonjour {getattr(client, 'full_name', '') or ''},\n\n"
                f"Votre code de confirmation pour valider le devis {quote.number} est : {validation.code}\n\n"
                f"Ce code expire dans 15 minutes."
            ),
            'rows': [
                {'label': 'Devis', 'value': quote.number},
                {'label': 'Code', 'value': validation.code},
            ],
            'action_url': code_url,
            'action_label': 'Saisir le code',
        },
    )

    # HTML ONLY
    email = EmailMessage(subject=subject, body=html, from_email=from_email, to=[recipient])
    email.content_subtype = 'html'
    email.send(fail_silently=False)
