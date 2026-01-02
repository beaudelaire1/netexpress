"""
Email service for sending professional notifications.
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


class EmailService:
    """Service for sending professional HTML emails."""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@netexpress.fr')
    
    def send_invoice_notification(self, invoice):
        """Send invoice notification email to client."""
        if not invoice.quote or not invoice.quote.client:
            return False
        
        client = invoice.quote.client
        if not client.email:
            return False
        
        # Render email template
        context = {
            'invoice': invoice,
            'client': client,
            'client_name': client.full_name if hasattr(client, 'full_name') else str(client),
            'company_name': getattr(settings, 'INVOICE_BRANDING', {}).get('name', 'NetExpress'),
            'branding': getattr(settings, 'INVOICE_BRANDING', {}),
        }
        
        html_content = render_to_string('emails/invoice_notification.html', context)
        text_content = strip_tags(html_content)
        
        subject = f'Facture {invoice.number} - {context["company_name"]}'
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=self.from_email,
            to=[client.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Attach PDF - generate fresh for ephemeral filesystem
        try:
            pdf_bytes = invoice.generate_pdf(attach=False)
            email.attach(f"facture_{invoice.number}.pdf", pdf_bytes, 'application/pdf')
        except Exception:
            pass  # Continue without attachment if generation fails
        
        try:
            email.send()
            return True
        except Exception:
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