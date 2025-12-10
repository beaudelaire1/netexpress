from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from core.pdf import render_pdf
from .models import Quote


@receiver(post_save, sender=Quote)
def send_quote_with_pdf(sender, instance, created, **kwargs):
    """
    Envoi automatique du devis au client par e-mail avec le PDF joint.
    """
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
    html_body = render_to_string("messaging/email_base.html", {
        "subject": subject,
        "content": f"""
            <p>Bonjour {getattr(client, 'full_name', '')},</p>
            <p>Veuillez trouver ci-joint votre <strong>devis</strong> à signer et nous retourner avec la mention <em>Bon pour accord</em>.</p>
            <p>Cordialement,<br>Nettoyage Express</p>
        """
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
