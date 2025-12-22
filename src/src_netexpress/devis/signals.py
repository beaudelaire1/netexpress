from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from core.pdf import render_pdf
from .models import Quote
from core.services.notification_service import notification_service


@receiver(post_save, sender=Quote)
def handle_quote_validation(sender, instance, created, **kwargs):
    """
    Handle automatic client account creation when quote is validated (accepted).
    """
    # Skip during tests unless explicitly enabled
    if getattr(settings, 'TESTING', True):
        return
        
    # Only trigger on status change to ACCEPTED, not on creation
    if created:
        return
        
    # Check if quote was just accepted
    if instance.status == Quote.QuoteStatus.ACCEPTED:
        from accounts.services import ClientAccountCreationService
        from core.services.email_service import EmailService
        
        try:
            # Create client account if it doesn't exist
            user, was_created = ClientAccountCreationService.create_from_quote_validation(instance)
            
            if was_created:
                # Send invitation email for new accounts
                EmailService.send_client_invitation(user, instance)
            
            # Send notification about quote validation
            notification_service.notify_quote_validation(instance)
                
        except Exception as e:
            # Log error but don't break the quote validation process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create client account for quote {instance.pk}: {e}")


@receiver(post_save, sender=Quote)
def send_quote_with_pdf(sender, instance, created, **kwargs):
    """
    Envoi automatique du devis au client par e-mail avec le PDF joint.
    """
    # Skip email sending during tests
    if hasattr(settings, 'TESTING') or 'test' in str(settings.DATABASES['default']['NAME']):
        return
        
    if not created:
        return

    client = getattr(instance, "client", None)
    to_addr = getattr(client, "email", None) if client else None
    if not to_addr:
        return

    # Préparer le contexte PDF (identique à celui des factures)
    items = []
    if hasattr(instance, "quote_items"):
        for qi in instance.quote_items.all():
            items.append({
                "description": qi.description,
                "unit_price": qi.unit_price,
                "quantity": qi.quantity,
                "total_ht": qi.total_ht,
            })

    totals = {
        "total_ht": getattr(instance, "total_ht", ""),
        "tva": getattr(instance, "tva", ""),
        "total_ttc": getattr(instance, "total_ttc", ""),
    }
    branding = getattr(settings, "INVOICE_BRANDING", {"name": "Nettoyage Express"})
    context = {
        "branding": branding,
        "title": f"DEVIS #{getattr(instance,'number',instance.pk)}",
        "client": client,
        "items": items,
        "totals": totals,
        "footer_note": "Validité du devis : 30 jours. Conditions de paiement à réception.",
        "is_quote": True,
    }

    # Générer le PDF
    pdf_bytes = render_pdf("pdf/quote.html", context)
    file_name = f"devis-{getattr(instance,'number',instance.pk)}.pdf"

    # Construire le message HTML
    subject = f"[NetExpress] Votre devis #{getattr(instance,'number',instance.pk)}"
    
    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    html_body = render_to_string("emails/new_quote_pdf.html", {
        "quote": instance,
        "branding": branding,
        "cta_url": None  # Pas de lien pour l'instant
    })

    # Envoi du mail
    msg = EmailMultiAlternatives(
        subject=subject,
        body="Veuillez trouver votre devis en pièce jointe.",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_addr],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.attach(file_name, pdf_bytes, "application/pdf")
    msg.send()
