"""Services utilitaires pour l'application ``messaging``.

Ce module fournit des fonctions de haut niveau pour créer et
envoyer des messages en fonction de différents événements du site,
comme une demande de contact.  Il s'appuie sur le modèle
``EmailMessage`` pour persister les données et sur
``EmailNotificationService`` pour effectuer l'envoi.
"""

from django.conf import settings

from .models import EmailMessage

try:
    # Importer le service SMTP pour envoyer les notifications directement
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
    # Construire l'objet et le corps du message
    subject = f"Nouveau message de contact – {contact_message.get_topic_display()}"
    body_lines = [
        f"Nom : {contact_message.full_name}",
        f"Email : {contact_message.email}",
        f"Téléphone : {contact_message.phone}",
        f"Ville : {contact_message.city}",
        f"Code postal : {contact_message.zip_code}",
        "",  # ligne vide
        contact_message.body,
    ]
    body = "\n".join(body_lines)
    # Envoyer directement via le service SMTP si disponible
    if EmailNotificationService:
        EmailNotificationService.send(
            to_email=recipient,
            subject=subject,
            body=body,
            from_email_override=recipient,
        )
    else:
        # Fallback : enregistrer et envoyer via EmailMessage (sans override)
        email_obj = EmailMessage.objects.create(
            recipient=recipient,
            subject=subject,
            body=body,
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
    # Envoyer directement via le service SMTP si disponible
    if EmailNotificationService:
        EmailNotificationService.send(
            to_email=recipient,
            subject=subject,
            body=body,
            from_email_override=recipient,
        )
        return None
    else:
        # Fallback : enregistrer et envoyer via EmailMessage (sans override)
        email_obj = EmailMessage.objects.create(
            recipient=recipient,
            subject=subject,
            body=body,
        )
        email_obj.send()
        return email_obj