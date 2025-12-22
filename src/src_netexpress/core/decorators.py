"""
Portal access control decorators.

These decorators enforce role-based access control for portal-specific views.
They work in conjunction with the RoleBasedAccessMiddleware to provide
fine-grained access control at the view level.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.template.response import TemplateResponse


def get_user_role(user):
    """Get the user's role from their profile."""
    try:
        return user.profile.role
    except AttributeError:
        return 'client'  # Default role for users without profiles


def get_portal_redirect_url(user):
    """Get the appropriate portal URL for a user based on their role."""
    if user.is_staff or user.is_superuser:
        return '/admin-dashboard/'
    
    role = get_user_role(user)
    if role == 'worker':
        return '/worker/'
    else:  # client or default
        return '/client/'


def client_portal_required(view_func):
    """
    Decorator that restricts access to Client Portal views.
    
    Allows access to:
    - Users with role='client'
    - Staff and superusers (for testing/support)
    
    Redirects other users to their appropriate portal.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Allow staff and superusers
        if user.is_staff or user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user has client role
        user_role = get_user_role(user)
        if user_role == 'client':
            return view_func(request, *args, **kwargs)
        
        # Redirect to appropriate portal
        return redirect(get_portal_redirect_url(user))
    
    return _wrapped_view


def worker_portal_required(view_func):
    """
    Decorator that restricts access to Worker Portal views.
    
    Allows access to:
    - Users with role='worker'
    - Staff and superusers (for testing/support)
    
    Redirects other users to their appropriate portal.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Allow staff and superusers
        if user.is_staff or user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user has worker role
        user_role = get_user_role(user)
        if user_role == 'worker':
            return view_func(request, *args, **kwargs)
        
        # Redirect to appropriate portal
        return redirect(get_portal_redirect_url(user))
    
    return _wrapped_view


def admin_portal_required(view_func):
    """
    Decorator that restricts access to Admin Portal views.
    
    Allows access to:
    - Staff users (is_staff=True)
    - Superusers (is_superuser=True)
    
    Redirects other users to their appropriate portal.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Check if user is staff or superuser
        if user.is_staff or user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Redirect to appropriate portal
        return redirect(get_portal_redirect_url(user))
    
    return _wrapped_view


def portal_access_required(allowed_roles=None):
    """
    Flexible decorator that allows access based on specified roles.
    
    Args:
        allowed_roles (list): List of allowed roles ('client', 'worker', 'admin')
                             If None, allows all authenticated users.
    
    Usage:
        @portal_access_required(['client', 'worker'])
        def some_view(request):
            # Accessible to clients and workers only
            pass
    """
    if allowed_roles is None:
        allowed_roles = ['client', 'worker', 'admin']
    
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Always allow staff and superusers
            if user.is_staff or user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check user role
            user_role = get_user_role(user)
            
            # Map roles to check against allowed_roles
            if 'admin' in allowed_roles and (user.is_staff or user.is_superuser):
                return view_func(request, *args, **kwargs)
            
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # Redirect to appropriate portal
            return redirect(get_portal_redirect_url(user))
        
        return _wrapped_view
    return decorator


def ajax_portal_access_required(allowed_roles=None):
    """
    Decorator for AJAX views that need portal access control.
    
    Returns HTTP 403 Forbidden instead of redirecting for AJAX requests.
    """
    if allowed_roles is None:
        allowed_roles = ['client', 'worker', 'admin']
    
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Always allow staff and superusers
            if user.is_staff or user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check user role
            user_role = get_user_role(user)
            
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # Return 403 for AJAX requests instead of redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponseForbidden("Access denied")
            
            # Redirect for regular requests
            return redirect(get_portal_redirect_url(user))
        
        return _wrapped_view
    return decorator