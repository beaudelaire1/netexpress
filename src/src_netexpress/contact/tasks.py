"""
Celery tasks for contact notifications (admin emails).
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Mock decorator si Celery n'est pas disponible
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


def send_contact_notification(message_id: int) -> None:
    """Version synchrone de l'envoi de notification de contact."""
    from contact.models import Message  # local import

    try:
        msg = Message.objects.get(pk=message_id)
    except Message.DoesNotExist:
        return

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    context = {"msg": msg, "branding": branding}
    
    # Vérifier si le template existe, sinon utiliser un contenu simple
    try:
        html = render_to_string("emails/new_contact_admin.html", context)
    except:
        # Template simple si le fichier n'existe pas
        html = f"""
        <h2>Nouveau message de contact</h2>
        <p><strong>Nom:</strong> {msg.full_name}</p>
        <p><strong>Email:</strong> {msg.email}</p>
        <p><strong>Téléphone:</strong> {getattr(msg, 'phone', 'Non renseigné')}</p>
        <p><strong>Sujet:</strong> {msg.get_topic_display()}</p>
        <p><strong>Ville:</strong> {getattr(msg, 'city', 'Non renseignée')}</p>
        <p><strong>Message:</strong></p>
        <p>{getattr(msg, 'body', 'Aucun message')}</p>
        """

    # recipients
    recipients = []
    if getattr(settings, "ADMINS", None):
        recipients.extend([email for _, email in settings.ADMINS if email])
    if not recipients:
        fallback = getattr(settings, "TASK_NOTIFICATION_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL", None)
        if fallback:
            recipients.append(fallback)
    if not recipients:
        # Utiliser l'email de test comme fallback
        recipients.append("vilmebeaudelaire5@gmail.com")

    # Use EmailMultiAlternatives for HTML emails to work with Brevo backend
    from django.core.mail import EmailMultiAlternatives
    from django.utils.html import strip_tags
    
    text_body = strip_tags(html)
    email = EmailMultiAlternatives(
        subject=f"[Contact] Nouveau message — {msg.full_name}",
        body=text_body,
        to=recipients,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "vilmebeaudelaire5@gmail.com"),
    )
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=False)


if CELERY_AVAILABLE:
    @shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
    def notify_new_contact(self, message_id: int) -> None:
        return send_contact_notification(message_id)
else:
    def notify_new_contact(message_id: int) -> None:
        return send_contact_notification(message_id)
