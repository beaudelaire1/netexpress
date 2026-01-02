"""
Email service for sending professional notifications.
"""

import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)


def _safe_client_name(invoice):
    """Extrait le nom du client de manière sécurisée."""
    try:
        if hasattr(invoice, 'quote') and invoice.quote and hasattr(invoice.quote, 'client'):
            client = invoice.quote.client
            return getattr(client, 'full_name', '') or getattr(client, 'name', '') or 'Client'
    except Exception:
        pass
    return 'Client'


class EmailService:
    """Service for sending professional HTML emails."""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@netexpress.fr')
    
    def _get_invoice_recipients(self, invoice):
        """Récupère les destinataires de la facture."""
        recipients = []
        try:
            if hasattr(invoice, 'quote') and invoice.quote and hasattr(invoice.quote, 'client'):
                client = invoice.quote.client
                if hasattr(client, 'email') and client.email:
                    recipients.append(client.email)
        except Exception as e:
            logger.error(f"Error getting invoice recipients: {e}")
        return recipients
    
    def send_invoice_notification(self, invoice):
        """Send invoice notification email to client using Django template.
        
        Parameters
        ----------
        invoice : Invoice
            The invoice instance to send notification for
        
        Returns
        -------
        bool
            True if email sent successfully, False otherwise
        """
        # Get recipients
        recipients = self._get_invoice_recipients(invoice)
        if not recipients:
            logger.warning(f"No recipients found for invoice {getattr(invoice, 'number', 'unknown')}")
            return False
        
        # Build context for the template
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        client_name = _safe_client_name(invoice)
        context = {
            'invoice': invoice,
            'branding': branding,
            'client_name': client_name,
        }
        
        subject = f"Votre facture {getattr(invoice, 'number', '')}"
        
        # Try to use Brevo with Django template if configured
        if getattr(settings, "EMAIL_BACKEND", "").endswith("BrevoEmailBackend"):
            try:
                from core.services.brevo_email_service import BrevoEmailService
                from core.services.document_generator import DocumentGenerator
                
                brevo = BrevoEmailService()
                if brevo.api_instance:
                    # Generate PDF
                    pdf_file = DocumentGenerator.generate_pdf(invoice, "pdf/invoice_premium.html", "FAC")
                    
                    # Send to each recipient
                    success = True
                    for recipient in recipients:
                        sent = brevo.send_with_django_template(
                            to_email=recipient,
                            subject=subject,
                            template_name="emails/invoice_notification.html",
                            context=context,
                            attachments=[(pdf_file.filename, pdf_file.content)],
                        )
                        if not sent:
                            success = False
                            logger.warning(f"Failed to send invoice via Brevo to {recipient}")
                    
                    if success:
                        return True
                    # If any failed, fall through to Django email
            except Exception as e:
                logger.error(f"Error sending invoice via Brevo: {e}", exc_info=True)
                # Fall through to Django email
        
        # Fallback: use Django EmailMultiAlternatives
        html_content = render_to_string('emails/invoice_notification.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=self.from_email,
            to=recipients
        )
        email.attach_alternative(html_content, "text/html")
        
        # Attach PDF if available
        if hasattr(invoice, 'pdf') and invoice.pdf:
            try:
                email.attach_file(invoice.pdf.path)
            except Exception as e:
                logger.warning(f"Could not attach invoice PDF: {e}")
        
        try:
            email.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False
    
    def send_quote_pdf_to_client(self, quote):
        """Send quote PDF to client using Django template."""
        # Get client email
        if not hasattr(quote, 'client') or not quote.client:
            logger.warning(f"No client found for quote {getattr(quote, 'number', 'unknown')}")
            return False
        
        client = quote.client
        if not hasattr(client, 'email') or not client.email:
            logger.warning(f"No email found for client in quote {getattr(quote, 'number', 'unknown')}")
            return False
        
        # Build context for the template
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        context = {
            'quote': quote,
            'branding': branding,
            'cta_url': None,  # Could be added if there's a quote validation URL
        }
        
        subject = f"Votre devis {getattr(quote, 'number', '')}"
        
        # Try to use Brevo with Django template if configured
        if getattr(settings, "EMAIL_BACKEND", "").endswith("BrevoEmailBackend"):
            try:
                from core.services.brevo_email_service import BrevoEmailService
                from core.services.document_generator import DocumentGenerator
                
                brevo = BrevoEmailService()
                if brevo.api_instance:
                    # Generate PDF
                    pdf_file = DocumentGenerator.generate_pdf(quote, "pdf/quote_premium.html", "DEV")
                    
                    # Send email
                    sent = brevo.send_with_django_template(
                        to_email=client.email,
                        subject=subject,
                        template_name="emails/new_quote_pdf.html",
                        context=context,
                        attachments=[(pdf_file.filename, pdf_file.content)],
                    )
                    
                    if sent:
                        return True
                    logger.warning(f"Failed to send quote via Brevo to {client.email}")
                    # Fall through to Django email
            except Exception as e:
                logger.error(f"Error sending quote via Brevo: {e}", exc_info=True)
                # Fall through to Django email
        
        # Fallback: use Django EmailMultiAlternatives
        html_content = render_to_string('emails/new_quote_pdf.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=self.from_email,
            to=[client.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Attach PDF if available
        if hasattr(quote, 'pdf') and quote.pdf:
            try:
                email.attach_file(quote.pdf.path)
            except Exception as e:
                logger.warning(f"Could not attach quote PDF: {e}")
        # Attach PDF - generate fresh for ephemeral filesystem
        try:
            pdf_bytes = invoice.generate_pdf(attach=False)
            email.attach(f"facture_{invoice.number}.pdf", pdf_bytes, 'application/pdf')
        except Exception:
            pass  # Continue without attachment if generation fails
        
        try:
            email.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send quote email: {e}")
            return False
    
    @staticmethod
    def send_client_invitation(user, quote, request=None):
        """
        Send account invitation email to new client.
        
        Args:
            user: User instance for the new client account
            quote: Quote instance that triggered the account creation
            request: Optional request object for building absolute URLs
        """
        if not user.email:
            return False
            
        # Generate password reset token for account setup
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build password setup URL
        base_url = EmailService._get_base_url(request)
        password_setup_url = f"{base_url}{reverse('accounts:password_setup', kwargs={'uidb64': uid, 'token': token})}"
        
        # Get client information
        client = getattr(quote, 'client', None)
        client_name = getattr(client, 'full_name', '') if client else user.get_full_name() or user.username
        
        # Render email template
        context = {
            'user': user,
            'client_name': client_name,
            'quote': quote,
            'password_setup_url': password_setup_url,
            'company_name': getattr(settings, 'INVOICE_BRANDING', {}).get('name', 'NetExpress'),
        }
        
        html_content = render_to_string('emails/account_invitation.html', context)
        text_content = strip_tags(html_content)
        
        subject = f'Bienvenue chez {context["company_name"]} - Configurez votre compte'
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@netexpress.fr'),
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send invitation email to {user.email}: {e}")
            return False
    
    @staticmethod
    def _get_base_url(request=None):
        """Get base URL for building absolute links."""
        if request is not None:
            try:
                return request.build_absolute_uri('/').rstrip('/')
            except Exception:
                pass
        return str(getattr(settings, 'SITE_URL', 'http://localhost:8000')).rstrip('/')


# Backward compatibility alias
PremiumEmailService = EmailService