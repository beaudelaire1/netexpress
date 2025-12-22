from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
import re


class RoleBasedAccessMiddleware:
    """
    Middleware to enforce portal boundaries based on user roles.
    
    Portal URL patterns:
    - /client/... -> Client Portal (requires role='client')
    - /worker/... -> Worker Portal (requires role='worker') 
    - /admin-dashboard/... -> Admin Portal (requires staff/superuser)
    - /admin/... -> Django Admin (requires staff/superuser)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define portal URL patterns
        self.portal_patterns = {
            'client': re.compile(r'^/client/'),
            'worker': re.compile(r'^/worker/'),
            'admin_dashboard': re.compile(r'^/admin-dashboard/'),
            'django_admin': re.compile(r'^/gestion/'),  # Updated to match actual admin URL
        }
        
        # URLs that should be accessible to all authenticated users
        self.public_urls = [
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/signup/',
            '/accounts/password-setup/',
            '/contact/',
            '/services/',
            '/devis/',
            '/static/',
            '/media/',
            '/ckeditor/',
            '/sitemap.xml',
            '/robots.txt',
        ]
        
        # Root URL patterns that should be accessible
        self.root_public_patterns = [
            re.compile(r'^/$'),  # Exact root URL only
            re.compile(r'^/a-propos/$'),
            re.compile(r'^/excellence/$'),
            re.compile(r'^/realisations/$'),
            re.compile(r'^/health/$'),
        ]
        
    def __call__(self, request):
        # Skip middleware for public URLs
        if any(request.path.startswith(url) for url in self.public_urls):
            response = self.get_response(request)
            return response
            
        # Check root public patterns
        if any(pattern.match(request.path) for pattern in self.root_public_patterns):
            response = self.get_response(request)
            return response
            
        # Skip middleware for anonymous users (let Django's auth handle it)
        if isinstance(request.user, AnonymousUser):
            response = self.get_response(request)
            return response
            
        # Check portal access for authenticated users
        redirect_response = self._check_portal_access(request)
        if redirect_response:
            return redirect_response
            
        # Update last portal access time
        self._update_portal_access_time(request)
        
        response = self.get_response(request)
        return response
        
    def _check_portal_access(self, request):
        """Check if user has access to the requested portal"""
        path = request.path
        user = request.user
        
        # Get user profile and role
        try:
            profile = user.profile
            user_role = profile.role
        except AttributeError:
            # User has no profile, treat as client
            user_role = 'client'
            
        # Check Client Portal access
        if self.portal_patterns['client'].match(path):
            if user_role != 'client' and not user.is_staff and not user.is_superuser:
                return self._redirect_to_appropriate_portal(user)
                
        # Check Worker Portal access  
        elif self.portal_patterns['worker'].match(path):
            if user_role != 'worker' and not user.is_staff and not user.is_superuser:
                return self._redirect_to_appropriate_portal(user)
                
        # Check Admin Dashboard access
        elif self.portal_patterns['admin_dashboard'].match(path):
            if not user.is_staff and not user.is_superuser:
                return self._redirect_to_appropriate_portal(user)
                
        # Check Django Admin access
        elif self.portal_patterns['django_admin'].match(path):
            if not user.is_staff and not user.is_superuser:
                return self._redirect_to_appropriate_portal(user)
                
        return None
        
    def _redirect_to_appropriate_portal(self, user):
        """Redirect user to their appropriate portal based on role"""
        try:
            profile = user.profile
            user_role = profile.role
        except AttributeError:
            user_role = 'client'
            
        # Staff and superusers go to admin dashboard
        if user.is_staff or user.is_superuser:
            return redirect('/admin-dashboard/')
            
        # Workers go to worker portal
        elif user_role == 'worker':
            return redirect('/worker/')
            
        # Clients go to client portal
        else:
            return redirect('/client/')
            
    def _update_portal_access_time(self, request):
        """Update the user's last portal access time"""
        try:
            profile = request.user.profile
            profile.last_portal_access = timezone.now()
            profile.save(update_fields=['last_portal_access'])
        except AttributeError:
            # User has no profile, skip update
            pass


def get_user_portal_redirect_url(user):
    """
    Utility function to get the appropriate portal URL for a user.
    Can be used by views and other components for consistent redirects.
    """
    try:
        profile = user.profile
        user_role = profile.role
    except AttributeError:
        user_role = 'client'
        
    # Staff and superusers go to admin dashboard
    if user.is_staff or user.is_superuser:
        return '/admin-dashboard/'
        
    # Workers go to worker portal
    elif user_role == 'worker':
        return '/worker/'
        
    # Clients go to client portal
    else:
        return '/client/'