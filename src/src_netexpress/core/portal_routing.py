"""
Utilities de routing des portails NetExpress.

NB: La source de vérité des rôles + mapping rôle -> URL est dans `accounts.portal`.
Ce module conserve une API stable utilisée par templates/middlewares/tests.
"""

from django.shortcuts import redirect

from accounts.portal import (
    get_user_role,
    get_portal_home_url,
    redirect_after_login,
    redirect_to_user_portal,
    get_portal_area_from_url,
    is_portal_url,
    user_can_access_portal_area,
)


def get_portal_type_from_url(path):
    """
    Retourne le type de portail depuis une URL.

    Historique:
    - Cette fonction est consommée par le tracking et les tests.
    - On distingue désormais `admin_dashboard` (business) et `gestion` (technique).
    """
    return get_portal_area_from_url(path)


def user_can_access_portal(user, portal_type):
    """
    Compat: wrapper sur `accounts.portal.user_can_access_portal_area`.
    """
    if not portal_type:
        return True
    return user_can_access_portal_area(user, portal_type)


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
        if self.user_role == 'admin_business':
            return '/admin-dashboard/messages/'
        elif self.user_role == 'admin_technical':
            return '/gestion/'
        elif self.user_role == 'worker':
            return '/worker/messages/'
        else:  # client
            return '/client/messages/'
    
    def get_notifications_url(self):
        """Get the notifications URL for the user's portal."""
        if self.user_role == 'admin_business':
            return '/admin-dashboard/notifications/'
        elif self.user_role == 'admin_technical':
            return '/gestion/'
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