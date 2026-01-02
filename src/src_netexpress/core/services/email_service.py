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

from django.core.mail import get_connection

from .pdf_service import InvoicePdfService, QuotePdfService


def _get_email_backend():
    """Retourne le service d'envoi d'e-mail approprié.
    
    Import is done inside the function to allow graceful degradation
    if Brevo SDK is not installed or not configured. This pattern
    ensures the code works even without the optional Brevo dependency.
    """
    if getattr(settings, "USE_BREVO_API", False):
        try:
            from core.services.brevo_email_service import BrevoEmailService
            return BrevoEmailService()
        except Exception:
            pass
    return None  # Fallback sur Django EmailMultiAlternatives


def _safe_client_name(obj) -> str:
    """Try to extract a human friendly client name from quote/invoice."""
    try:
        quote = getattr(obj, "quote", None) or obj
        client = getattr(quote, "client", None)
        if client is None:
            return "Cher client"
        return (
            getattr(client, "full_name", None)
            or (f"{getattr(client, 'first_name', '')} {getattr(client, 'last_name', '')}".strip())
            or getattr(client, "email", None)
            or "Cher client"
        )
    except Exception:
        return "Cher client"


class PremiumEmailService:
    """Service responsible for sending premium emails (devis + factures).

    Important: this service uses Django's email backend directly.
    It does **not** depend on Celery being up.
    """

    def __init__(
        self,
        invoice_pdf_service: Optional[InvoicePdfService] = None,
        quote_pdf_service: Optional[QuotePdfService] = None,
    ) -> None:
        self.invoice_pdf_service = invoice_pdf_service or InvoicePdfService()
        self.quote_pdf_service = quote_pdf_service or QuotePdfService()

    def _get_invoice_recipients(self, invoice) -> List[str]:
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

    def _get_quote_recipient(self, quote) -> Optional[str]:
        """Best effort to find the client's email for a quote."""
        client = getattr(quote, "client", None)
        if client is not None:
            email = getattr(client, "email", None)
            if email:
                return email
        for attr in ("email", "client_email", "contact_email"):
            val = getattr(quote, attr, None)
            if val:
                return val
        return None

    def _get_admin_recipient(self) -> Optional[str]:
        return getattr(settings, "NETEXPRESS_DEVIS_NOTIFICATION", None) or getattr(
            settings, "TASK_NOTIFICATION_EMAIL", None
        )

    def send_invoice_notification(self, invoice) -> None:
        """Send an invoice notification email with PDF attached.

        Parameters
        ----------
        invoice: django.db.models.Model
            An instance of the Invoice model to be sent.  It should
            provide access to the client and totals, and will be
            passed to the PDF generator and the e‑mail templates.
        """
        # Generate the PDF attachment (always before sending)
        pdf_file = self.invoice_pdf_service.generate(invoice)

        # Build e‑mail subject and recipients
        subject = f"Votre facture {getattr(invoice, 'number', '')}"
        recipients = self._get_invoice_recipients(invoice)
        if not recipients:
            raise RuntimeError("Aucun destinataire e-mail détecté pour cette facture.")
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or (getattr(settings, "INVOICE_BRANDING", {}) or {}).get("email")

        # Prepare context for the HTML template.  Compute the client name
        # from the invoice's related quote if available.
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        client_name = _safe_client_name(invoice)
        context = {
            "invoice": invoice,
            "branding": branding,
            "client_name": client_name,
        }
        html_body = render_to_string("emails/invoice_notification.html", context)
        text_body = strip_tags(html_body)

        # Try using Brevo API if configured
        brevo_service = _get_email_backend()
        if brevo_service:
            try:
                # recipients[0] is safe here because we validated recipients is not empty above
                success = brevo_service.send(
                    to_email=recipients[0],  # Brevo service sends to one recipient
                    subject=subject,
                    body=text_body,
                    html_body=html_body,
                    from_email=from_email,
                    attachments=[(pdf_file.filename, pdf_file.content)],
                )
                if success:
                    return
            except Exception:
                # Fallback to SMTP if Brevo fails
                pass

        # Fallback: use Django EmailMultiAlternatives (SMTP)
        email = EmailMultiAlternatives(subject, text_body, from_email, recipients)
        # Attach HTML alternative
        email.attach_alternative(html_body, "text/html")
        # Attach PDF
        email.attach(pdf_file.filename, pdf_file.content, pdf_file.mimetype)
        # Send (fail loudly so you *see* the problem in dev/prod logs)
        email.send(fail_silently=False)

    def send_quote_pdf_to_client(self, quote, *, acceptance_url: Optional[str] = None) -> None:
        """Send a premium quote email with an attached PDF.

        This method guarantees PDF generation *before* sending.
        """
        to_email = self._get_quote_recipient(quote)
        if not to_email:
            raise RuntimeError("Aucun email client détecté pour ce devis.")

        pdf_file = self.quote_pdf_service.generate(quote)

        # Persist PDF on the model so the back-office can retrieve it later.
        try:
            from django.core.files.base import ContentFile
            if getattr(quote, "pdf", None) is not None:
                # Always overwrite to keep the latest version.
                quote.pdf.save(pdf_file.filename, ContentFile(pdf_file.content), save=True)
        except Exception:
            # Don't block email sending if storage fails (e.g. read-only FS).
            pass
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        cta_url = acceptance_url or None

        context = {
            "quote": quote,
            "branding": branding,
            "cta_url": cta_url,
        }
        subject = f"Votre devis {getattr(quote, 'number', '')}".strip()
        html_body = render_to_string("emails/new_quote_pdf.html", context)
        text_body = strip_tags(html_body)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or branding.get("email")

        # Try using Brevo API if configured
        brevo_service = _get_email_backend()
        if brevo_service:
            try:
                success = brevo_service.send(
                    to_email=to_email,
                    subject=subject,
                    body=text_body,
                    html_body=html_body,
                    from_email=from_email,
                    attachments=[(pdf_file.filename, pdf_file.content)],
                )
                if success:
                    return
            except Exception:
                # Fallback to SMTP if Brevo fails
                pass

        # Fallback: use Django EmailMultiAlternatives (SMTP)
        email = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
        email.attach_alternative(html_body, "text/html")
        email.attach(pdf_file.filename, pdf_file.content, pdf_file.mimetype)
        email.send(fail_silently=False)

    def notify_admin_quote_created(self, quote) -> None:
        """Notify admin that a quote was created (no attachment)."""
        recipient = self._get_admin_recipient()
        if not recipient:
            return
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        subject = f"[NetExpress] Nouveau devis {getattr(quote,'number', quote.pk)}"
        client = getattr(quote, "client", None)
        client_label = getattr(client, "full_name", None) or getattr(client, "email", None) or "Client"
        body = (
            f"Un nouveau devis vient d'être créé.\n"
            f"Client: {client_label}\n"
            f"Total TTC: {getattr(quote, 'total_ttc', '')}\n"
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or branding.get("email")
        EmailMultiAlternatives(subject, body, from_email, [recipient]).send(fail_silently=False)