
from __future__ import annotations
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Invoice
from messaging.models import EmailMessage
from factures import Invoice
@receiver(post_save, sender=Invoice)
def notify_invoice_created(sender, instance: Invoice, created: bool, **kwargs) -> None:
    if not created:
        return
    recipient = getattr(settings, "TASK_NOTIFICATION_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", ""))
    if not recipient:
        return
    num =  Invoice.number #getattr(instance, "invoice.number", None)
    subject = f"[Nettoyage Express] Facture #{num} générée".format(num=instance.number or instance.pk)
    total = Invoice.total_ttc #getattr(instance, "total_ttc", None) or getattr(instance, "total", "")
    body =f"Une nouvelle facture #{num} a été générée. Total TTC: {total}".format(num=instance.number or instance.pk, total=total)
    EmailMessage.objects.create(recipient=recipient, subject=subject, body=body).send()
