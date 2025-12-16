"""Signals for the ``factures`` app.

Goals:
- Keep signals side-effects **minimal** and **observable**.
- Do NOT depend on Celery.
- Do NOT silently swallow SMTP errors.

We intentionally avoid sending client invoices from a signal because
invoice creation can happen in multiple contexts (admin action, service
layer, management command). The canonical place for sending is the
service layer / explicit action.

Here we only create an internal message record for auditability.
"""

from __future__ import annotations

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Invoice


@receiver(post_save, sender=Invoice)
def notify_admin_invoice_created(sender, instance: Invoice, created: bool, **kwargs) -> None:
    """Create an internal notification entry when an invoice is created."""
    if not created:
        return

    recipient = getattr(settings, "TASK_NOTIFICATION_EMAIL", None) or getattr(
        settings, "NETEXPRESS_DEVIS_NOTIFICATION", None
    )
    if not recipient:
        return

    try:
        from messaging.models import EmailMessage as DbEmailMessage
    except Exception:
        return

    num = instance.number or str(instance.pk)
    total = getattr(instance, "total_ttc", "")
    subject = f"[NetExpress] Facture {num} créée"
    body = f"Une nouvelle facture {num} a été créée. Total TTC: {total}"

    # We store the message for traceability; sending can be manual from the dashboard.
    DbEmailMessage.objects.create(recipient=recipient, subject=subject, body=body)
