from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags


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

    # Ensure we have a stable public token for links (backfill if legacy data)
    if not getattr(quote, 'public_token', None):
        try:
            quote.save(update_fields=["public_token"])
        except Exception:
            try:
                quote.save()
            except Exception:
                pass

    base = _base_url(request)
    # Public PDF link uses Quote.public_token (stable).
    # Validation link must point to the START step with the *public_token*.
    # IMPORTANT: Per requirement, the OTP code MUST NOT appear in the quote email.
    # It is sent in a separate email when the client clicks the validation link.
    pdf_url = f"{base}{reverse('devis:quote_public_pdf', kwargs={'token': quote.public_token})}"
    validation_url = f"{base}{reverse('devis:quote_validate_start', kwargs={'token': quote.public_token})}"

    client = getattr(quote, 'client', None)
    client_name = getattr(client, 'full_name', '') if client is not None else ''
    recipient = to_email or (getattr(client, 'email', None) if client is not None else None)
    if not recipient:
        return

    subject = f"Votre devis {quote.number} — {getattr(settings, 'INVOICE_BRANDING', {}).get('name', 'Nettoyage Express')}"
    company_name = getattr(settings, 'INVOICE_BRANDING', {}).get('name', 'Nettoyage Express')

    # Optional custom message (edited in back-office, HTML allowed)
    custom_message = (getattr(quote, "email_body_html", "") or "").strip() or None

    html_body = render_to_string(
        'emails/modele_quote.html',
        {
            'quote': quote,
            'client_name': client_name or 'Bonjour',
            'company_name': company_name,
            'pdf_url': pdf_url,
            'validation_url': validation_url,
            'custom_message': custom_message,
        },
    )

    # Plain-text fallback (required)
    text_lines = [
        f"Bonjour {client_name or ''}",
        "",
        f"Voici votre devis {quote.number}.",
        f"Consulter le devis : {pdf_url}",
        "",
        "Pour valider le bon pour accord :", 
        f"1) Cliquez sur le lien : {validation_url}",
        "2) Vous recevrez un code séparément", 
        "3) La validation ne sera effective qu'après saisie du code.",
        "",
        "Cordialement,",
        company_name,
    ]
    text_body = "\n".join([l for l in text_lines if l is not None])

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@example.com'
    msg = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=[recipient])
    msg.attach_alternative(html_body, 'text/html')

    # Attach PDF
    try:
        if quote.pdf and hasattr(quote.pdf, 'open'):
            with quote.pdf.open('rb') as f:
                msg.attach(f"{quote.number}.pdf", f.read(), 'application/pdf')
    except Exception:
        pass

    msg.send(fail_silently=False)


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
                f"Le bon pour accord sera validé uniquement après saisie du code.\n\n"
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
    text_body = strip_tags(html)
    email = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=[recipient])
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=False)
