"""
Celery tasks for messaging module.

Background tasks for sending emails asynchronously.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_async(self, recipient, subject, body, html_body=None):
    """Send an email asynchronously.
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
    
    Returns:
        bool: True if email was sent successfully
    """
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_body,
            fail_silently=False,
        )
        return True
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_message_async(self, email_message_id):
    """Send an EmailMessage by ID asynchronously.
    
    Args:
        email_message_id: ID of the EmailMessage to send
    
    Returns:
        bool: True if email was sent successfully
    """
    from .models import EmailMessage
    
    try:
        msg = EmailMessage.objects.get(id=email_message_id)
        msg.send()
        return True
    except EmailMessage.DoesNotExist:
        return False
    except Exception as exc:
        raise self.retry(exc=exc)
