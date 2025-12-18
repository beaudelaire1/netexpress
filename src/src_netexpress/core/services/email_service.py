"""
Service module for sending premium invoice notification e‑mails.

The :class:`PremiumEmailService` encapsulates the steps required to
create a multipart e‑mail containing both plain text and HTML
representations, attach the generated invoice PDF and send it to the
appropriate recipient(s).  By centralising this logic in a service,
views and other layers remain uncluttered and maintainable.
"""

from __future__ import annotations

from typing import List, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .pdf_service import InvoicePdfService


class PremiumEmailService:
    """Service responsible for sending invoice notifications by e‑mail."""

    def __init__(self, pdf_service: Optional[InvoicePdfService] = None) -> None:
        self.pdf_service = pdf_service or InvoicePdfService()

    def _get_recipients(self, invoice) -> List[str]:
        """Determine the e‑mail recipients for the given invoice.

        This implementation attempts to use the client e‑mail
        associated with the invoice's quote.  If unavailable, it
        falls back to a configured address in ``INVOICE_BRANDING`` or
        ``DEFAULT_TO_EMAIL`` in settings.
        """
        recipients: List[str] = []
        # Try to use the quote's client email if present
        quote = getattr(invoice, "quote", None)
        if quote and getattr(quote, "client", None):
            email = getattr(quote.client, "email", None)
            if email:
                recipients.append(email)
        # Fallback: try invoice.client_email (domain)
        email = getattr(invoice, "client_email", None)
        if email:
            recipients.append(email)
        # Finally, use default configured recipient if none found
        if not recipients:
            branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
            fallback = branding.get("email") or getattr(settings, "DEFAULT_TO_EMAIL", None)
            if fallback:
                recipients.append(fallback)
        return recipients

    def send_invoice_notification(self, invoice) -> None:
        """Send an invoice notification email with PDF attached.

        Parameters
        ----------
        invoice: django.db.models.Model
            An instance of the Invoice model to be sent.  It should
            provide access to the client and totals, and will be
            passed to the PDF generator and the e‑mail templates.
        """
        # Generate the PDF attachment
        pdf_file = self.pdf_service.generate(invoice)

        # Build e‑mail subject and recipients
        subject = f"Votre facture {getattr(invoice, 'number', '')}"
        recipients = self._get_recipients(invoice)
        if not recipients:
            # If we cannot determine recipients, abort silently
            return
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or (getattr(settings, "INVOICE_BRANDING", {}) or {}).get("email")

        # Prepare context for the HTML template.  Compute the client name
        # from the invoice's related quote if available.
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        client_name = None
        try:
            if hasattr(invoice, "quote") and invoice.quote and getattr(invoice.quote, "client", None):
                client_name = invoice.quote.client.full_name or invoice.quote.client.first_name or invoice.quote.client.last_name
        except Exception:
            client_name = None
        if not client_name:
            # Fall back to any attribute defined on the invoice itself
            client_name = getattr(invoice, "client_name", None) or "Cher client"
        context = {
            "invoice": invoice,
            "branding": branding,
            "client_name": client_name,
        }
        html_body = render_to_string("emails/invoice_notification.html", context)
        text_body = strip_tags(html_body)

        # Create the email
        email = EmailMultiAlternatives(subject, text_body, from_email, recipients)
        # Attach HTML alternative
        email.attach_alternative(html_body, "text/html")
        # Attach PDF
        email.attach(pdf_file.filename, pdf_file.content, pdf_file.mimetype)
        # Send
        email.send()