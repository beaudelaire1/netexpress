"""
Portal routing utilities.

This module provides utilities for handling portal-specific routing logic,
including automatic redirects based on user roles and portal access validation.
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect


def get_user_role(user):
    """
    Get the user's role from their profile.
    
    Args:
        user: Django User instance
        
    Returns:
        str: User role ('client', 'worker', or 'admin')
    """
    if user.is_staff or user.is_superuser:
        return 'admin'
    
    try:
        return user.profile.role
    except AttributeError:
        return 'client'  # Default role for users without profiles


def get_portal_home_url(user):
    """
    Get the home URL for a user's appropriate portal.
    
    Args:
        user: Django User instance
        
    Returns:
        str: Portal home URL
    """
    role = get_user_role(user)
    
    if role == 'admin':
        return '/admin-dashboard/'
    elif role == 'worker':
        return '/worker/'
    else:  # client
        return '/client/'


def redirect_to_user_portal(user):
    """
    Create a redirect response to the user's appropriate portal.
    
    Args:
        user: Django User instance
        
    Returns:
        HttpResponseRedirect: Redirect to appropriate portal
    """
    portal_url = get_portal_home_url(user)
    return redirect(portal_url)


def redirect_after_login(user):
    """
    Determine where to redirect a user after successful login.
    
    Args:
        user: Django User instance
        
    Returns:
        str: URL to redirect to after login
    """
    return get_portal_home_url(user)


def is_portal_url(path):
    """
    Check if a URL path belongs to any portal.
    
    Args:
        path (str): URL path to check
        
    Returns:
        bool: True if path is a portal URL
    """
    portal_prefixes = ['/client/', '/worker/', '/admin-dashboard/']
    return any(path.startswith(prefix) for prefix in portal_prefixes)


def get_portal_type_from_url(path):
    """
    Determine which portal a URL belongs to.
    
    Args:
        path (str): URL path to analyze
        
    Returns:
        str: Portal type ('client', 'worker', 'admin') or None if not a portal URL
    """
    if path.startswith('/client/'):
        return 'client'
    elif path.startswith('/worker/'):
        return 'worker'
    elif path.startswith('/admin-dashboard/'):
        return 'admin'
    else:
        return None


def user_can_access_portal(user, portal_type):
    """
    Check if a user can access a specific portal type.
    
    Args:
        user: Django User instance
        portal_type (str): Portal type ('client', 'worker', 'admin')
        
    Returns:
        bool: True if user can access the portal
    """
    user_role = get_user_role(user)
    
    # Staff and superusers can access any portal
    if user.is_staff or user.is_superuser:
        return True
    
    # Regular users can only access their own portal type
    return user_role == portal_type


def validate_portal_access(user, path):
    """
    Validate if a user can access a specific portal URL.
    
    Args:
        user: Django User instance
        path (str): URL path to validate
        
    Returns:
        tuple: (can_access: bool, redirect_url: str or None)
    """
    portal_type = get_portal_type_from_url(path)
    
    # If not a portal URL, allow access
    if not portal_type:
        return True, None
    
    # Check if user can access this portal
    if user_can_access_portal(user, portal_type):
        return True, None
    
    # User cannot access this portal, provide redirect URL
    redirect_url = get_portal_home_url(user)
    return False, redirect_url


def handle_portal_redirect(request):
    """
    Handle portal redirect logic for authenticated users.
    
    This function should be called when a user accesses a URL that requires
    portal-specific access control. It will redirect them to the appropriate
    portal if they don't have access to the requested one.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponseRedirect or None: Redirect response if needed, None otherwise
    """
    if not request.user.is_authenticated:
        return None
    
    path = request.path
    can_access, redirect_url = validate_portal_access(request.user, path)
    
    if not can_access and redirect_url:
        return redirect(redirect_url)
    
    return None


class PortalRouter:
    """
    Class-based portal routing utility for more complex routing logic.
    """
    
    def __init__(self, user):
        self.user = user
        self.user_role = get_user_role(user)
    
    def get_dashboard_url(self):
        """Get the dashboard URL for the user's portal."""
        return get_portal_home_url(self.user)
    
    def get_messages_url(self):
        """Get the messages URL for the user's portal."""
        if self.user_role == 'admin':
            return '/admin-dashboard/messages/'
        elif self.user_role == 'worker':
            return '/worker/messages/'
        else:  # client
            return '/client/messages/'
    
    def get_notifications_url(self):
        """Get the notifications URL for the user's portal."""
        if self.user_role == 'admin':
            return '/admin-dashboard/notifications/'
        elif self.user_role == 'worker':
            return '/worker/notifications/'
        else:  # client
            return '/client/notifications/'
    
    def can_access_url(self, path):
        """Check if the user can access a specific URL."""
        can_access, _ = validate_portal_access(self.user, path)
        return can_access
    
    def get_redirect_if_needed(self, path):
        """Get redirect URL if user cannot access the requested path."""
        can_access, redirect_url = validate_portal_access(self.user, path)
        return redirect_url if not can_access else None