"""Services utilitaires pour l'application ``messaging``.

Ce module fournit des fonctions de haut niveau pour créer et
envoyer des messages en fonction de différents événements du site,
comme une demande de contact.  Il s'appuie sur le modèle
``EmailMessage`` pour persister les données et sur
``EmailNotificationService`` pour effectuer l'envoi.
"""

from django.conf import settings

from .models import EmailMessage


def send_contact_notification(contact_message: "contact.models.Message") -> EmailMessage:
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
    dest = getattr(settings, "CONTACT_RECEIVER_EMAIL", "")
    if not dest:
        dest = getattr(settings, "DEFAULT_FROM_EMAIL", "")
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
    # Créer et envoyer l'e‑mail
    email_obj = EmailMessage.objects.create(
        recipient=recipient,
        subject=subject,
        body=body,
    )
    # Envoyer immédiatement
    email_obj.send()
    return email_obj