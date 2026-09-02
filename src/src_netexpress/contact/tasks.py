"""
Notification interne à la réception d'un message de contact.

L'aiguillage synchrone/Celery et le traitement des échecs sont communs à tous
les formulaires publics : voir ``core.notifications``.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string

from core.notifications import send_notification

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:  # Celery est optionnel : le mode synchrone suffit.
    CELERY_AVAILABLE = False

    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


def _recipients() -> tuple[list[str], list[str]]:
    """Destinataire principal et copies, tels que configurés dans l'environnement."""
    primary = (
        getattr(settings, "CONTACT_RECEIVER_EMAIL", "")
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    ).strip()

    cc_raw = getattr(settings, "CONTACT_CC_EMAIL", "") or ""
    cc = [addr.strip() for addr in cc_raw.split(",") if addr.strip()]

    return ([primary] if primary else []), cc


def _plain_text_body(msg) -> str:
    """Version texte, lue par les clients qui refusent le HTML et par les antispams."""
    return "\n".join(
        [
            "Nouveau message de contact",
            "",
            f"Nom      : {msg.full_name}",
            f"Email    : {msg.email}",
            f"Téléphone: {msg.phone or '—'}",
            f"Sujet    : {msg.get_topic_display()}",
            f"Adresse  : {msg.street or '—'}, {msg.zip_code} {msg.city}".strip(),
            "",
            "Message :",
            msg.body or "—",
        ]
    )


def send_contact_notification(message_id: int) -> None:
    """Envoie la notification admin. Lève si l'envoi échoue, pour être journalisé."""
    from contact.models import Message  # import local : évite un cycle au chargement

    try:
        msg = Message.objects.get(pk=message_id)
    except Message.DoesNotExist:
        logger.warning("Notification de contact ignorée : message %s introuvable", message_id)
        return

    recipients, cc = _recipients()
    if not recipients:
        # Sans destinataire, mieux vaut un journal explicite qu'un envoi muet
        # vers une adresse arbitraire.
        logger.error(
            "Message de contact %s enregistré mais non notifié : ni CONTACT_RECEIVER_EMAIL "
            "ni DEFAULT_FROM_EMAIL ne sont configurés.",
            message_id,
        )
        return

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    context = {"msg": msg, "branding": branding}

    text_body = _plain_text_body(msg)
    try:
        html_body = render_to_string("emails/new_contact_admin.html", context)
    except TemplateDoesNotExist:
        logger.warning("Gabarit emails/new_contact_admin.html absent : envoi en texte brut.")
        html_body = ""

    email = EmailMultiAlternatives(
        subject=f"[Contact] Nouveau message — {msg.full_name}",
        body=text_body,
        to=recipients,
        cc=cc or None,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        # Répondre au courriel écrit directement au demandeur.
        reply_to=[msg.email] if getattr(msg, "email", None) else None,
    )
    if html_body:
        email.attach_alternative(html_body, "text/html")

    email.send(fail_silently=False)
    logger.info("Notification de contact %s envoyée à %s", message_id, ", ".join(recipients))


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def notify_new_contact_task(self, message_id: int) -> None:
    """Variante Celery, utilisée uniquement si NOTIFY_EMAILS_ASYNC est actif."""
    return send_contact_notification(message_id)


def notify_new_contact(message_id: int) -> bool:
    """Point d'entrée unique des vues. Retourne True si la notification est partie."""
    return send_notification(
        f"message de contact {message_id}",
        send_contact_notification,
        args=(message_id,),
        celery_task=notify_new_contact_task if CELERY_AVAILABLE else None,
    )
