"""
Celery tasks for contact notifications (admin emails).
"""

from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def notify_new_contact(self, message_id: int) -> None:
    from contact.models import Message  # local import

    msg = Message.objects.get(pk=message_id)

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    context = {"msg": msg, "branding": branding}
    html = render_to_string("emails/new_contact_admin.html", context)

    # recipients
    recipients = []
    if getattr(settings, "ADMINS", None):
        recipients.extend([email for _, email in settings.ADMINS if email])
    if not recipients:
        fallback = getattr(settings, "TASK_NOTIFICATION_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL", None)
        if fallback:
            recipients.append(fallback)
    if not recipients:
        return

    email = EmailMessage(
        subject=f"[Contact] Nouveau message — {msg.full_name}",
        body=html,
        to=recipients,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
    )
    email.content_subtype = "html"
    email.send(fail_silently=False)
