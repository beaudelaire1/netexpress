"""Services utilitaires pour l'application ``messaging``.

Ce module fournit des fonctions de haut niveau pour créer et
envoyer des messages en fonction de différents événements du site,
comme une demande de contact.  Il s'appuie sur le modèle
``EmailMessage`` pour persister les données et sur
``EmailNotificationService`` pour effectuer l'envoi.
"""

from django.conf import settings
from django.core.files.base import ContentFile

from .models import EmailMessage

try:
    # Service d'envoi HTML premium
    from tasks.services import EmailNotificationService  # type: ignore
except Exception:
    EmailNotificationService = None  # type: ignore


def send_contact_notification(contact_message: "contact.models.Message") -> None:
    """Envoyer une notification pour un message de contact.

    Cette fonction construit un e‑mail à partir d'une instance du
    modèle ``contact.Message`` et l'envoie aux destinataires
    configurés dans ``CONTACT_RECEIVER_EMAIL`` ou ``DEFAULT_FROM_EMAIL``.
    L'e‑mail est également enregistré dans la base de données afin
    d'être consulté ultérieurement dans le tableau de bord.

    Parameters
    ----------
    contact_message : contact.models.Message
        L'instance du message de contact à notifier.

    Returns
    -------
    EmailMessage
        L'objet d'e‑mail créé et envoyé.
    """
    # Déterminer le ou les destinataires.  Autoriser une liste séparée
    # par virgules dans les settings, sinon utiliser DEFAULT_FROM_EMAIL.
    # Déterminer le destinataire de la notification de contact.
    # Priorité : CONTACT_RECEIVER_EMAIL > DEFAULT_FROM_EMAIL > EMAIL_HOST_USER
    dest = getattr(settings, "CONTACT_RECEIVER_EMAIL", "")
    if not dest:
        dest = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not dest:
        dest = getattr(settings, "EMAIL_HOST_USER", "")
    recipient = dest or ""
    subject = f"Nouveau message de contact – {contact_message.get_topic_display()}"

    # Build context for Django template
    context = {
        "msg": contact_message,
        "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
    }

    # Try to use Brevo with Django template if configured
    if getattr(settings, "EMAIL_BACKEND", "").endswith("BrevoEmailBackend"):
        try:
            from core.services.brevo_email_service import BrevoEmailService
            
            brevo = BrevoEmailService()
            if brevo.api_instance:
                sent = brevo.send_with_django_template(
                    to_email=recipient,
                    subject=subject,
                    template_name="emails/new_contact_admin.html",
                    context=context,
                )
                
                if sent:
                    EmailMessage.objects.create(
                        recipient=recipient,
                        subject=subject,
                        body=contact_message.body or "Nouveau message de contact"
                    )
                    return None
        except Exception:
            # Fall through to existing implementation
            pass

    # Fallback: HTML ONLY (exigence projet)
    rows = [
        {"label": "Nom", "value": contact_message.full_name},
        {"label": "Email", "value": contact_message.email},
        {"label": "Téléphone", "value": contact_message.phone},
        {"label": "Ville", "value": contact_message.city or "—"},
        {"label": "Code postal", "value": contact_message.zip_code or "—"},
    ]
    intro = (contact_message.body or "").strip()
    if not intro:
        intro = "Un nouveau message a été envoyé depuis le formulaire de contact."

    if EmailNotificationService:
        EmailNotificationService.send(
            to=recipient,
            subject=subject,
            headline="Nouveau message de contact",
            intro=intro,
            rows=rows,
        )
        EmailMessage.objects.create(recipient=recipient, subject=subject, body=intro)
    else:
        # Fallback : e-mail HTML minimal via EmailMessage
        email_obj = EmailMessage.objects.create(
            recipient=recipient,
            subject=subject,
            body=intro,
        )
        email_obj.send()
    return None


def send_quote_notification(quote: "devis.models.Quote") -> EmailMessage:
    """Envoyer une notification pour une demande de devis.

    Cette fonction construit un e‑mail à partir d'une instance du
    modèle ``devis.Quote`` et l'envoie au destinataire configuré
    dans ``QUOTE_RECEIVER_EMAIL``.  À défaut, l'e‑mail est envoyé
    à l'adresse définie dans ``DEFAULT_FROM_EMAIL``.  Le message est
    également enregistré en base via ``EmailMessage``.

    Parameters
    ----------
    quote : devis.models.Quote
        L'instance du devis à notifier.  Les informations du client
        (nom, email, téléphone) ainsi que le service demandé et le
        message libre sont inclus dans le corps.

    Returns
    -------
    EmailMessage
        L'objet d'e‑mail créé et envoyé.
    """
    # Déterminer le destinataire principal
    dest = getattr(settings, "QUOTE_RECEIVER_EMAIL", "")
    if not dest:
        dest = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not dest:
        dest = getattr(settings, "EMAIL_HOST_USER", "")
    recipient = dest or ""
    # Construire le sujet et le corps
    subject = f"Nouvelle demande de devis — {quote.number}"
    client = quote.client
    
    # Build context for Django template
    context = {
        "quote": quote,
        "client": client,
        "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
    }
    
    # Préparer la pièce jointe PDF si disponible (before trying Brevo)
    attachments_list = None
    try:
        if quote.pdf:
            attachments_list = [(quote.pdf.name.rsplit("/", 1)[-1], quote.pdf.read())]
    except Exception:
        attachments_list = None
    
    # Try to use Brevo with Django template if configured
    if getattr(settings, "EMAIL_BACKEND", "").endswith("BrevoEmailBackend"):
        try:
            from core.services.brevo_email_service import BrevoEmailService
            
            brevo = BrevoEmailService()
            if brevo.api_instance:
                sent = brevo.send_with_django_template(
                    to_email=recipient,
                    subject=subject,
                    template_name="emails/new_quote.html",
                    context=context,
                    attachments=attachments_list,
                )
                
                if sent:
                    body = f"Devis {quote.number} — {client.full_name}"
                    EmailMessage.objects.create(recipient=recipient, subject=subject, body=body)
                    return None
        except Exception:
            # Fall through to existing implementation
            pass
    
    service_title = quote.service.title if quote.service else "—"
    body_lines = [
        f"Nom : {client.full_name}",
        f"Email : {client.email}",
        f"Téléphone : {client.phone}",
        f"Service demandé : {service_title}",
    ]
    # Ajouter le message si présent
    if quote.message:
        body_lines.extend(["", "Message :", quote.message])
    body = "\n".join(body_lines)

    # Construire une version HTML plus lisible pour le devis
    html_body = None
    try:
        # Construire une table des items s'il y en a
        items_html = ""
        if hasattr(quote, "items"):
            rows = []
            for item in quote.items:
                label = item.description or (item.service.title if item.service else "")
                rows.append(
                    f"<tr><td style='padding:4px 8px;border:1px solid #ddd;'>{label}</td>"
                    f"<td style='padding:4px 8px;border:1px solid #ddd;' align='right'>{item.quantity}</td>"
                    f"<td style='padding:4px 8px;border:1px solid #ddd;' align='right'>{item.unit_price:.2f} €</td>"
                    f"<td style='padding:4px 8px;border:1px solid #ddd;' align='right'>{item.tax_rate:.2f}%</td>"
                    f"<td style='padding:4px 8px;border:1px solid #ddd;' align='right'>{item.total_ttc:.2f} €</td></tr>"
                )
            items_html = (
                "<table style='border-collapse:collapse;width:100%;font-size:14px;'>"
                "<thead><tr style='background:#f5f7f9;'>"
                "<th style='padding:6px 8px;border:1px solid #ddd;'>Description</th>"
                "<th style='padding:6px 8px;border:1px solid #ddd;'>Qté</th>"
                "<th style='padding:6px 8px;border:1px solid #ddd;'>PU HT</th>"
                "<th style='padding:6px 8px;border:1px solid #ddd;'>TVA %</th>"
                "<th style='padding:6px 8px;border:1px solid #ddd;'>Total TTC</th>"
                "</tr></thead><tbody>"
                + "".join(rows)
                + "</tbody></table>"
            )

        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        company_name = branding.get("name", "Nettoyage Express")
        html_body = f"""
        <html>
        <body style="font-family:Arial,Helvetica,sans-serif;color:#333;">
        <p>Bonjour {client.full_name},</p>
        <p>Merci de votre demande de devis. Voici votre proposition :</p>
        {items_html}
        <p><strong>Total HT :</strong> {quote.total_ht:.2f} €</p>
        <p><strong>TVA :</strong> {quote.tva:.2f} €</p>
        <p><strong>Total TTC :</strong> {quote.total_ttc:.2f} €</p>
        {f"<p><em>Ce devis est valable jusqu'au {quote.valid_until.strftime('%d/%m/%Y')}</em></p>" if quote.valid_until else ''}
        <p><em>Veuillez répondre avec la mention « Bon pour accord » pour l'accepter.</em></p>
        <p>Cordialement,<br>{company_name}</p>
        </body>
        </html>
        """
    except Exception:
        html_body = None

    # Préparer la pièce jointe PDF si disponible
    attachments = None
    try:
        if quote.pdf:
            attachments = [(quote.pdf.name.rsplit("/", 1)[-1], quote.pdf.read())]
    except Exception:
        attachments = None

    # Envoyer directement via le service SMTP premium si disponible
    if EmailNotificationService:
        EmailNotificationService.send(
            to=recipient,
            subject=subject,
            headline="Nouvelle demande de devis",
            intro=f"Devis {quote.number} — {client.full_name}",
            rows=[
                {"label": "Client", "value": client.full_name},
                {"label": "Email", "value": client.email},
                {"label": "Téléphone", "value": client.phone},
                {"label": "Total TTC", "value": f"{quote.total_ttc:.2f} €"},
            ],
        )
        EmailMessage.objects.create(recipient=recipient, subject=subject, body=body)
        return None
    else:
        # Fallback : enregistrer et envoyer via EmailMessage
        email_obj = EmailMessage.objects.create(
            recipient=recipient,
            subject=subject,
            body=body,
        )
        # Attacher le PDF au modèle EmailMessage
        if attachments:
            try:
                fname, content = attachments[0]
                email_obj.attachment.save(fname, ContentFile(content), save=False)
            except Exception:
                pass
        email_obj.save()
        email_obj.send()
        return email_obj