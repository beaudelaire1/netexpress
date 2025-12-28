"""
Modèles de l'application ``core``.

Cette application contient les modèles pour la gestion des portails clients
et le contrôle d'accès aux documents.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ClientDocument(models.Model):
    """Links clients to their accessible documents for access tracking."""
    
    client_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='accessible_documents',
        help_text="Client user who has access to this document"
    )
    quote = models.ForeignKey(
        'devis.Quote', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='client_accesses',
        help_text="Quote document accessible to the client"
    )
    invoice = models.ForeignKey(
        'factures.Invoice', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='client_accesses',
        help_text="Invoice document accessible to the client"
    )
    access_granted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When access was granted to this document"
    )
    last_accessed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the client last accessed this document"
    )
    
    class Meta:
        verbose_name = "Client Document Access"
        verbose_name_plural = "Client Document Accesses"
        unique_together = [
            ('client_user', 'quote'),
            ('client_user', 'invoice'),
        ]
        indexes = [
            models.Index(fields=['client_user', 'access_granted_at']),
            models.Index(fields=['quote', 'client_user']),
            models.Index(fields=['invoice', 'client_user']),
        ]
    
    def clean(self):
        """Validate that at least one of quote or invoice is set, and not both."""
        from django.core.exceptions import ValidationError
        
        if not self.quote and not self.invoice:
            raise ValidationError("Au moins un de 'quote' ou 'invoice' doit être défini.")
        if self.quote and self.invoice:
            raise ValidationError("Un ClientDocument ne peut pas avoir à la fois un quote et une invoice.")
    
    def save(self, *args, **kwargs):
        """Override save to call clean validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.quote:
            return f"{self.client_user.username} -> Quote {self.quote.number}"
        elif self.invoice:
            return f"{self.client_user.username} -> Invoice {self.invoice.number}"
        return f"{self.client_user.username} -> Unknown Document"
    
    def update_last_accessed(self):
        """Update the last accessed timestamp."""
        from django.utils import timezone
        self.last_accessed_at = timezone.now()
        self.save(update_fields=['last_accessed_at'])


__all__ = ['ClientDocument', 'UINotification', 'PortalSession']


class PortalSession(models.Model):
    """Track user portal sessions for analytics and usage patterns.
    
    Records when users access different portals, helping administrators
    understand usage patterns and optimize the user experience.
    """
    
    PORTAL_TYPES = [
        ('client', 'Client Portal'),
        ('worker', 'Worker Portal'),
        ('admin', 'Admin Portal'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='portal_sessions',
        help_text="User who accessed the portal"
    )
    portal_type = models.CharField(
        max_length=20,
        choices=PORTAL_TYPES,
        help_text="Type of portal accessed"
    )
    login_time = models.DateTimeField(
        auto_now_add=True,
        help_text="When the user logged into the portal"
    )
    logout_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user logged out or session ended"
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the user's session"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string from the browser"
    )
    pages_visited = models.PositiveIntegerField(
        default=0,
        help_text="Number of pages visited during this session"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        help_text="Last activity timestamp for this session"
    )
    session_duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Total duration of the session (calculated on logout)"
    )
    
    class Meta:
        verbose_name = "Portal Session"
        verbose_name_plural = "Portal Sessions"
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
            models.Index(fields=['portal_type', '-login_time']),
            models.Index(fields=['ip_address', '-login_time']),
            models.Index(fields=['-login_time']),
        ]
    
    def __str__(self):
        duration = self.get_session_duration()
        return f"{self.user.username} - {self.get_portal_type_display()} ({duration})"
    
    def get_session_duration(self):
        """Calculate and return session duration."""
        if self.logout_time:
            duration = self.logout_time - self.login_time
        else:
            # Session still active, calculate current duration
            duration = timezone.now() - self.login_time
        
        # Format duration nicely
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def end_session(self):
        """End the session and calculate duration."""
        if not self.logout_time:
            self.logout_time = timezone.now()
            self.session_duration = self.logout_time - self.login_time
            self.save(update_fields=['logout_time', 'session_duration'])
    
    def increment_page_visit(self):
        """Increment the page visit counter."""
        self.pages_visited += 1
        self.last_activity = timezone.now()
        self.save(update_fields=['pages_visited', 'last_activity'])
    
    @classmethod
    def start_session(cls, user, portal_type, request):
        """Start a new portal session."""
        # Get IP address from request
        ip_address = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # End any existing active sessions for this user/portal
        active_sessions = cls.objects.filter(
            user=user,
            portal_type=portal_type,
            logout_time__isnull=True
        )
        for session in active_sessions:
            session.end_session()
        
        # Create new session
        return cls.objects.create(
            user=user,
            portal_type=portal_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or '127.0.0.1'
    
    @classmethod
    def get_user_sessions(cls, user, days=30):
        """Get recent sessions for a user."""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return cls.objects.filter(
            user=user,
            login_time__gte=cutoff_date
        ).order_by('-login_time')
    
    @classmethod
    def get_portal_analytics(cls, portal_type=None, days=30):
        """Get analytics data for portal usage."""
        from datetime import timedelta
        from django.db.models import Count, Avg, Sum
        
        cutoff_date = timezone.now() - timedelta(days=days)
        queryset = cls.objects.filter(login_time__gte=cutoff_date)
        
        if portal_type:
            queryset = queryset.filter(portal_type=portal_type)
        
        return {
            'total_sessions': queryset.count(),
            'unique_users': queryset.values('user').distinct().count(),
            'avg_session_duration': queryset.aggregate(
                avg_duration=Avg('session_duration')
            )['avg_duration'],
            'total_page_views': queryset.aggregate(
                total_pages=Sum('pages_visited')
            )['total_pages'] or 0,
            'sessions_by_portal': queryset.values('portal_type').annotate(
                count=Count('id')
            ).order_by('-count')
        }


class UINotification(models.Model):
    """In-app notification system for portal users.
    
    Provides visual notifications for important events like task completion,
    quote validation, and account creation. Notifications appear in the UI
    and can be marked as read by users.
    """
    
    NOTIFICATION_TYPES = [
        ('task_completed', 'Task Completed'),
        ('task_assigned', 'Task Assigned'),
        ('quote_validated', 'Quote Validated'),
        ('invoice_created', 'Invoice Created'),
        ('message_received', 'Message Received'),
        ('account_created', 'Account Created'),
        ('document_updated', 'Document Updated'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ui_notifications',
        help_text="User who will receive this notification"
    )
    title = models.CharField(
        max_length=200,
        help_text="Short notification title"
    )
    message = models.TextField(
        help_text="Detailed notification message"
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='general',
        help_text="Type of notification for categorization and styling"
    )
    read = models.BooleanField(
        default=False,
        help_text="Whether the user has read this notification"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the notification was created"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was marked as read"
    )
    link_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional URL to link to related content"
    )
    
    class Meta:
        verbose_name = "UI Notification"
        verbose_name_plural = "UI Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read', '-created_at']),
            models.Index(fields=['user', 'notification_type']),
        ]
    
    def __str__(self):
        status = "Read" if self.read else "Unread"
        return f"{self.title} - {self.user.username} ({status})"
    
    def mark_as_read(self):
        """Mark the notification as read."""
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save(update_fields=['read', 'read_at'])
    
    def mark_as_unread(self):
        """Mark the notification as unread."""
        if self.read:
            self.read = False
            self.read_at = None
            self.save(update_fields=['read', 'read_at'])
    
    @classmethod
    def get_unread_count(cls, user):
        """Get the count of unread notifications for a user."""
        return cls.objects.filter(user=user, read=False).count()
    
    @classmethod
    def get_recent_notifications(cls, user, limit=10):
        """Get recent notifications for a user."""
        return cls.objects.filter(user=user).order_by('-created_at')[:limit]