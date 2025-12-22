"""
Session tracking middleware for portal analytics.

Tracks user sessions across different portals to provide usage analytics
and help optimize the user experience.
"""

from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from core.models import PortalSession
from core.portal_routing import get_portal_type_from_url, get_user_role


class PortalSessionTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track portal sessions and page visits.
    
    This middleware:
    1. Tracks when users access different portals
    2. Records page visits within portal sessions
    3. Updates session activity timestamps
    4. Provides analytics data for portal usage
    """
    
    def process_request(self, request):
        """Process incoming requests to track portal activity."""
        # Only track authenticated users
        if not request.user.is_authenticated:
            return None
        
        # Check if this is a portal URL
        portal_type = get_portal_type_from_url(request.path)
        if not portal_type:
            return None
        
        # Get or create current session
        session = self.get_or_create_session(request, portal_type)
        
        # Store session in request for later use
        request.portal_session = session
        
        return None
    
    def process_response(self, request, response):
        """Process responses to update session activity."""
        # Only process if we have a portal session
        if not hasattr(request, 'portal_session'):
            return response
        
        # Increment page visit counter for successful responses
        if 200 <= response.status_code < 400:
            request.portal_session.increment_page_visit()
        
        return response
    
    def get_or_create_session(self, request, portal_type):
        """Get existing session or create a new one."""
        user = request.user
        
        # Look for existing active session
        try:
            session = PortalSession.objects.get(
                user=user,
                portal_type=portal_type,
                logout_time__isnull=True
            )
            return session
        except PortalSession.DoesNotExist:
            # Create new session
            return PortalSession.start_session(user, portal_type, request)
        except PortalSession.MultipleObjectsReturned:
            # Multiple active sessions found, end all but the most recent
            sessions = PortalSession.objects.filter(
                user=user,
                portal_type=portal_type,
                logout_time__isnull=True
            ).order_by('-login_time')
            
            # Keep the most recent, end the others
            for session in sessions[1:]:
                session.end_session()
            
            return sessions[0]


@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """Handle user login to start portal session tracking."""
    # Determine which portal the user is accessing
    portal_type = get_portal_type_from_url(request.path)
    
    # If not accessing a specific portal, determine from user role
    if not portal_type:
        user_role = get_user_role(user)
        if user_role == 'admin':
            portal_type = 'admin'
        elif user_role == 'worker':
            portal_type = 'worker'
        else:
            portal_type = 'client'
    
    # Start session tracking
    PortalSession.start_session(user, portal_type, request)


@receiver(user_logged_out)
def handle_user_logout(sender, request, user, **kwargs):
    """Handle user logout to end portal sessions."""
    if user:
        # End all active sessions for this user
        active_sessions = PortalSession.objects.filter(
            user=user,
            logout_time__isnull=True
        )
        for session in active_sessions:
            session.end_session()


class SessionAnalyticsMiddleware(MiddlewareMixin):
    """
    Middleware to provide session analytics in templates.
    
    Adds session analytics data to the request context for use in templates.
    """
    
    def process_request(self, request):
        """Add session analytics to request context."""
        if request.user.is_authenticated:
            # Add user's recent sessions to context
            request.user_sessions = PortalSession.get_user_sessions(request.user, days=7)
            
            # Add portal analytics for admin users
            if request.user.is_staff:
                request.portal_analytics = PortalSession.get_portal_analytics(days=30)
        
        return None