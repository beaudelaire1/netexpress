"""
Signals for messaging app to trigger notifications.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message
from core.services.notification_service import notification_service


@receiver(post_save, sender=Message)
def message_created_handler(sender, instance, created, **kwargs):
    """
    Handle message creation to send notifications.
    """
    if created and instance.recipient:
        # Send notification to recipient
        notification_service.notify_message_received(instance)