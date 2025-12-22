"""
Backward compatibility layer for NetExpress v2 transformation.

This module provides compatibility functions and middleware to ensure
existing URLs and functionality continue to work during the transition
to the new portal-based architecture.
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from functools import wraps


def legacy_url_redirect(view_func):
    """
    Decorator to handle legacy URL redirects.
    
    This decorator can be applied to views that have been moved or renamed
    to automatically redirect to the new location while maintaining
    backward compatibility.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if this is a legacy URL pattern that needs redirection
        if hasattr(request, 'resolver_match') and request.resolver_match:
            url_name = request.resolver_match.url_name
            
            # Handle legacy dashboard redirects
            if url_name == 'dashboard' and request.user.is_authenticated:
                if hasattr(request.user, 'profile'):
                    if request.user.profile.role == 'client':
                        return redirect('core:client_portal_dashboard')
                    elif request.user.profile.role == 'worker':
                        return redirect('tasks:worker_dashboard')
                # Default to admin dashboard for staff
                if request.user.is_staff:
                    return redirect('core:admin_dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


class BackwardCompatibilityMiddleware:
    """
    Middleware to handle backward compatibility during the v2 transformation.
    
    This middleware intercepts requests to legacy URLs and redirects them
    to the appropriate new portal-based URLs based on the user's role.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define legacy URL mappings
        self.legacy_redirects = {
            '/dashboard/': self._handle_dashboard_redirect,
            '/dashboard/client/': 'core:client_portal_dashboard',
            '/dashboard/ouvrier/': 'tasks:worker_dashboard',
        }

    def __call__(self, request):
        # Check for legacy URL patterns before processing the request
        path = request.path_info
        
        if path in self.legacy_redirects:
            redirect_target = self.legacy_redirects[path]
            
            if callable(redirect_target):
                # Custom redirect logic
                response = redirect_target(request)
                if response:
                    return response
            else:
                # Simple URL redirect
                return HttpResponseRedirect(reverse(redirect_target))
        
        response = self.get_response(request)
        return response

    def _handle_dashboard_redirect(self, request):
        """Handle legacy dashboard URL redirects based on user role."""
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('accounts:login'))
        
        # Redirect based on user role
        if hasattr(request.user, 'profile') and request.user.profile:
            if request.user.profile.role == 'client':
                return HttpResponseRedirect(reverse('core:client_portal_dashboard'))
            elif request.user.profile.role == 'worker':
                return HttpResponseRedirect(reverse('tasks:worker_dashboard'))
        
        # Default to admin dashboard for staff users
        if request.user.is_staff or request.user.is_superuser:
            return HttpResponseRedirect(reverse('core:admin_dashboard'))
        
        # Fallback to home page
        return HttpResponseRedirect(reverse('core:home'))


def ensure_profile_exists(user):
    """
    Ensure a user has a profile with appropriate role.
    
    This function is used during the transition period to create
    profiles for existing users who don't have them yet.
    """
    if not hasattr(user, 'profile') or not user.profile:
        from accounts.models import Profile
        
        # Determine appropriate role
        if user.is_staff or user.is_superuser:
            role = Profile.ROLE_CLIENT  # Staff use admin, not portals
        elif user.groups.filter(name='Workers').exists():
            role = Profile.ROLE_WORKER
        else:
            role = Profile.ROLE_CLIENT
        
        Profile.objects.create(user=user, role=role)
        return True
    return False


def get_user_portal_url(user):
    """
    Get the appropriate portal URL for a user based on their role.
    
    Returns the URL name that the user should be redirected to
    based on their profile role and permissions.
    """
    if not user.is_authenticated:
        return 'accounts:login'
    
    # Ensure user has a profile
    ensure_profile_exists(user)
    
    # Staff users go to admin
    if user.is_staff or user.is_superuser:
        return 'core:admin_dashboard'
    
    # Role-based redirection
    if hasattr(user, 'profile') and user.profile:
        if user.profile.role == 'worker':
            return 'tasks:worker_dashboard'
        elif user.profile.role == 'client':
            return 'core:client_portal_dashboard'
    
    # Fallback
    return 'core:home'


class LegacyViewMixin:
    """
    Mixin for views that need to maintain backward compatibility.
    
    This mixin provides common functionality for handling legacy
    URL patterns and ensuring smooth transitions.
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure user has a profile if authenticated
        if request.user.is_authenticated:
            ensure_profile_exists(request.user)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add compatibility flags to context
        context['is_legacy_view'] = True
        context['portal_url'] = None
        
        if self.request.user.is_authenticated:
            context['portal_url'] = get_user_portal_url(self.request.user)
        
        return context