"""
Notification service for handling email and UI notifications.

This service provides a unified interface for sending notifications
across the NetExpress v2 platform, supporting both email notifications
and in-app UI notifications for various system events.
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.urls import reverse
from typing import Optional, List, Dict, Any

from core.models import UINotification


class NotificationService:
    """Unified service for email and UI notifications."""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@netexpress.fr')
    
    def create_ui_notification(
        self,
        user: User,
        title: str,
        message: str,
        notification_type: str = 'general',
        link_url: str = ''
    ) -> UINotification:
        """Create a UI notification for a user."""
        return UINotification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link_url=link_url
        )
    
    def send_email_notification(
        self,
        to_emails: List[str],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        attachment_path: Optional[str] = None
    ) -> bool:
        """Send an email notification using a template."""
        try:
            # Normalize template name (add emails/ prefix if not present)
            if not template_name.startswith('emails/'):
                full_template_name = f'emails/{template_name}.html'
            else:
                full_template_name = template_name if template_name.endswith('.html') else f'{template_name}.html'
            
            # Try to use Brevo with Django template if configured
            if getattr(settings, "EMAIL_BACKEND", "").endswith("BrevoEmailBackend"):
                try:
                    from core.services.brevo_email_service import BrevoEmailService
                    
                    brevo = BrevoEmailService()
                    if brevo.api_instance:
                        # Prepare attachments
                        attachments = None
                        if attachment_path:
                            try:
                                with open(attachment_path, 'rb') as f:
                                    filename = attachment_path.split('/')[-1]
                                    attachments = [(filename, f.read())]
                            except Exception:
                                pass
                        
                        # Send to each recipient
                        all_sent = True
                        for to_email in to_emails:
                            sent = brevo.send_with_django_template(
                                to_email=to_email,
                                subject=subject,
                                template_name=full_template_name,
                                context=context,
                                attachments=attachments,
                            )
                            if not sent:
                                all_sent = False
                        
                        if all_sent:
                            return True
                        # If any failed, fall through to Django email
                except Exception:
                    # Fall through to Django email
                    pass
            
            # Fallback: Render email content
            html_content = render_to_string(full_template_name, context)
            text_content = strip_tags(html_content)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=to_emails
            )
            email.attach_alternative(html_content, "text/html")
            
            # Attach file if provided
            if attachment_path:
                try:
                    email.attach_file(attachment_path)
                except Exception:
                    pass  # Continue without attachment if file not found
            
            email.send()
            return True
        except Exception:
            return False
    
    def notify_task_completion(self, task, completed_by: User) -> None:
        """Send notifications when a worker completes a task.
        
        Requirements: 3.4 - Task completion triggers invoice notification
        """
        # Create UI notification for admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            self.create_ui_notification(
                user=admin,
                title=f"Tâche terminée: {task.title}",
                message=f"La tâche '{task.title}' a été marquée comme terminée par {completed_by.get_full_name() or completed_by.username}.",
                notification_type='task_completed',
                link_url=f'/admin/tasks/task/{task.id}/change/'
            )
        
        # Send email notification to admin users
        admin_emails = [admin.email for admin in admin_users if admin.email]
        if admin_emails:
            context = {
                'task': task,
                'completed_by': completed_by,
                'company_name': 'NetExpress',
            }
            self.send_email_notification(
                to_emails=admin_emails,
                subject=f'Tâche terminée: {task.title}',
                template_name='task_completion',
                context=context
            )
    
    def notify_task_assignment(self, task, assigned_to: User) -> None:
        """Send notifications when a task is assigned to a worker."""
        # Create UI notification for the assigned worker
        self.create_ui_notification(
            user=assigned_to,
            title=f"Nouvelle tâche assignée: {task.title}",
            message=f"Une nouvelle tâche '{task.title}' vous a été assignée.",
            notification_type='task_assigned',
            link_url='/worker/dashboard/'
        )
        
        # Send email notification to the worker
        if assigned_to.email:
            context = {
                'task': task,
                'worker': assigned_to,
                'company_name': 'NetExpress',
            }
            self.send_email_notification(
                to_emails=[assigned_to.email],
                subject=f'Nouvelle tâche assignée: {task.title}',
                template_name='task_assignment',
                context=context
            )
    
    def notify_quote_validation(self, quote) -> None:
        """Send notifications when a quote is validated.
        
        Requirements: 6.4 - Quote validation triggers account creation and email invitation
        """
        # Create UI notification for admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            self.create_ui_notification(
                user=admin,
                title=f"Devis validé: {quote.number}",
                message=f"Le devis {quote.number} pour {quote.client.full_name if quote.client else 'client inconnu'} a été validé.",
                notification_type='quote_validated',
                link_url=f'/admin/devis/quote/{quote.id}/change/'
            )
        
        # If client has a user account, notify them
        if hasattr(quote.client, 'user') and quote.client.user:
            self.create_ui_notification(
                user=quote.client.user,
                title=f"Devis validé: {quote.number}",
                message=f"Votre devis {quote.number} a été validé et est maintenant disponible.",
                notification_type='quote_validated',
                link_url='/client/quotes/'
            )
            
            # Send email to client
            if quote.client.user.email:
                context = {
                    'quote': quote,
                    'client': quote.client,
                    'company_name': 'NetExpress',
                }
                self.send_email_notification(
                    to_emails=[quote.client.user.email],
                    subject=f'Devis validé: {quote.number}',
                    template_name='quote_validation',
                    context=context
                )
    
    def notify_invoice_creation(self, invoice) -> None:
        """Send notifications when an invoice is created."""
        # Create UI notification for admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            self.create_ui_notification(
                user=admin,
                title=f"Facture créée: {invoice.number}",
                message=f"La facture {invoice.number} a été créée.",
                notification_type='invoice_created',
                link_url=f'/admin/factures/invoice/{invoice.id}/change/'
            )
        
        # If client has a user account, notify them
        if hasattr(invoice, 'quote') and invoice.quote and hasattr(invoice.quote.client, 'user') and invoice.quote.client.user:
            client_user = invoice.quote.client.user
            self.create_ui_notification(
                user=client_user,
                title=f"Nouvelle facture: {invoice.number}",
                message=f"Une nouvelle facture {invoice.number} est disponible.",
                notification_type='invoice_created',
                link_url='/client/invoices/'
            )
    
    def notify_account_creation(self, user: User, password_reset_url: str) -> None:
        """Send notifications for automatic client account creation.
        
        Requirements: 6.4 - Send email invitation to set password
        """
        # Send email invitation to new client
        if user.email:
            context = {
                'user': user,
                'password_reset_url': password_reset_url,
                'company_name': 'NetExpress',
            }
            self.send_email_notification(
                to_emails=[user.email],
                subject='Bienvenue sur NetExpress - Configurez votre compte',
                template_name='account_invitation',
                context=context
            )
        
        # Create UI notification for admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            self.create_ui_notification(
                user=admin,
                title=f"Nouveau compte client créé: {user.get_full_name() or user.username}",
                message=f"Un compte client a été automatiquement créé pour {user.email}.",
                notification_type='account_created',
                link_url=f'/admin/auth/user/{user.id}/change/'
            )
    
    def notify_message_received(self, message) -> None:
        """Send notifications when a message is received."""
        # Create UI notification for the recipient
        self.create_ui_notification(
            user=message.recipient,
            title=f"Nouveau message: {message.subject}",
            message=f"Vous avez reçu un nouveau message de {message.sender.get_full_name() or message.sender.username}.",
            notification_type='message_received',
            link_url='/messaging/'
        )
        
        # Send email notification if recipient has email
        if message.recipient.email:
            context = {
                'message': message,
                'recipient': message.recipient,
                'sender': message.sender,
                'company_name': 'NetExpress',
            }
            self.send_email_notification(
                to_emails=[message.recipient.email],
                subject=f'Nouveau message: {message.subject}',
                template_name='message_notification',
                context=context
            )
    
    def notify_document_update(self, document, document_type: str, user: User) -> None:
        """Send notifications when a document is updated."""
        # Create UI notification for the user
        self.create_ui_notification(
            user=user,
            title=f"Document mis à jour: {document_type}",
            message=f"Le document {document_type} a été mis à jour.",
            notification_type='document_updated',
            link_url='/client/' if hasattr(user, 'profile') and user.profile.role == 'client' else '/admin-dashboard/'
        )
    
    def get_unread_notifications(self, user: User, limit: int = 10) -> List[UINotification]:
        """Get unread notifications for a user."""
        return UINotification.objects.filter(
            user=user,
            read=False
        ).order_by('-created_at')[:limit]
    
    def mark_notification_as_read(self, notification_id: int, user: User) -> bool:
        """Mark a notification as read for a user."""
        try:
            notification = UINotification.objects.get(id=notification_id, user=user)
            notification.mark_as_read()
            return True
        except UINotification.DoesNotExist:
            return False
    
    def mark_all_notifications_as_read(self, user: User) -> int:
        """Mark all notifications as read for a user."""
        from django.utils import timezone
        
        unread_notifications = UINotification.objects.filter(user=user, read=False)
        count = unread_notifications.count()
        unread_notifications.update(read=True, read_at=timezone.now())
        return count


# Global instance for easy import
notification_service = NotificationService()