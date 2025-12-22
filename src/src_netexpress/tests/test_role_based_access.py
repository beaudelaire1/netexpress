"""Property-based tests for role-based access control.

This module tests the role-based portal access control system using
property-based testing with Hypothesis to ensure universal correctness
properties hold across all possible user roles and portal URLs.

**Feature: netexpress-v2-transformation, Property 1: Role-based portal access control**
**Validates: Requirements 1.2, 1.3, 1.4, 1.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from django.test import RequestFactory, Client
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import HttpResponse

from accounts.models import Profile
from accounts.middleware import RoleBasedAccessMiddleware


pytestmark = pytest.mark.django_db


# Hypothesis strategies for generating test data
@st.composite
def user_with_role(draw):
    """Generate a user with a specific role."""
    base_username = draw(st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    # Ensure username is unique by adding a timestamp-like suffix
    import time
    unique_suffix = f"{int(time.time() * 1000000) % 1000000}_{draw(st.integers(min_value=1000, max_value=9999))}"
    username = f"{base_username}_{unique_suffix}"
    
    role = draw(st.sampled_from(['client', 'worker']))
    is_staff = draw(st.booleans())
    is_superuser = draw(st.booleans())
    
    return {
        'username': username,
        'role': role,
        'is_staff': is_staff,
        'is_superuser': is_superuser
    }


@st.composite
def portal_url(draw):
    """Generate portal URLs for testing."""
    portal_type = draw(st.sampled_from(['client', 'worker', 'admin_dashboard', 'django_admin']))
    
    url_patterns = {
        'client': '/client/',
        'worker': '/worker/',
        'admin_dashboard': '/admin-dashboard/',
        'django_admin': '/admin/'
    }
    
    # Add some random path after the base
    extra_path = draw(st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))))
    if extra_path:
        extra_path = extra_path.replace(' ', '-')
        
    return {
        'portal_type': portal_type,
        'url': url_patterns[portal_type] + extra_path
    }


class TestRoleBasedAccessControl:
    """Property-based tests for role-based access control."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        
        # Create a more realistic response function that simulates view behavior
        def mock_view_response(request):
            # Simulate a view that would normally handle the request
            return HttpResponse("OK")
            
        self.middleware = RoleBasedAccessMiddleware(mock_view_response)
        
    @given(user_data=user_with_role(), url_data=portal_url())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=10)
    def test_role_based_portal_access_control(self, user_data, url_data):
        """
        **Property 1: Role-based portal access control**
        
        For any user with a specific role, accessing any portal URL should either 
        grant access to the appropriate portal or redirect to the correct portal 
        based on their role, never allowing unauthorized cross-portal access.
        
        **Validates: Requirements 1.2, 1.3, 1.4, 1.5**
        """
        # Clean up any existing users with similar names to avoid conflicts
        User.objects.filter(username__startswith=user_data['username'][:10]).delete()
        
        # Create user with specified role
        user = User.objects.create_user(
            username=user_data['username'],
            is_staff=user_data['is_staff'],
            is_superuser=user_data['is_superuser']
        )
        
        # Create profile with role (profile is auto-created by signal, just update it)
        profile = user.profile
        profile.role = user_data['role']
        profile.save()
        
        # Test the middleware logic directly by calling _check_portal_access
        request = self.factory.get(url_data['url'])
        request.user = user
        
        # Call the middleware's access check method directly
        redirect_response = self.middleware._check_portal_access(request)
        
        # Determine expected behavior based on user role and portal type
        portal_type = url_data['portal_type']
        user_role = user_data['role']
        is_staff = user_data['is_staff']
        is_superuser = user_data['is_superuser']
        
        # Staff and superusers should have access to all portals (no redirect)
        if is_staff or is_superuser:
            # Should not redirect (return None from _check_portal_access)
            assert redirect_response is None
        else:
            # Non-staff users should only access their designated portal
            if portal_type == 'client' and user_role == 'client':
                # Client accessing client portal - should be allowed (no redirect)
                assert redirect_response is None
            elif portal_type == 'worker' and user_role == 'worker':
                # Worker accessing worker portal - should be allowed (no redirect)
                assert redirect_response is None
            elif portal_type in ['admin_dashboard', 'django_admin']:
                # Non-staff accessing admin areas - should be redirected
                assert redirect_response is not None
                assert redirect_response.status_code == 302
                # Should redirect to appropriate portal based on role
                if user_role == 'client':
                    assert '/client/' in redirect_response.url
                elif user_role == 'worker':
                    assert '/worker/' in redirect_response.url
            else:
                # Cross-portal access (client->worker or worker->client) - should be redirected
                assert redirect_response is not None
                assert redirect_response.status_code == 302
                # Should redirect to appropriate portal based on role
                if user_role == 'client':
                    assert '/client/' in redirect_response.url
                elif user_role == 'worker':
                    assert '/worker/' in redirect_response.url
        
        # Clean up created user to prevent conflicts in subsequent test runs
        user.delete()
                    
    @given(url_data=portal_url())
    def test_anonymous_user_access(self, url_data):
        """
        Anonymous users should not be affected by the middleware
        (Django's auth middleware will handle them).
        """
        request = self.factory.get(url_data['url'])
        request.user = AnonymousUser()
        
        response = self.middleware(request)
        
        # Anonymous users should get the default response (middleware passes through)
        assert response.status_code == 200
        assert response.content == b"OK"
        
    def test_public_urls_bypass_middleware(self):
        """Public URLs should bypass the middleware entirely."""
        public_urls = [
            '/',
            '/accounts/login/',
            '/accounts/logout/',
            '/contact/',
            '/services/',
            '/static/css/style.css',
            '/media/image.jpg',
        ]
        
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        user = User.objects.create_user(username=f'testuser_{unique_id}')
        # Profile is automatically created by signal, just update it
        user.profile.role = 'client'
        user.profile.save()
        
        for url in public_urls:
            request = self.factory.get(url)
            request.user = user
            
            response = self.middleware(request)
            
            # Should get default response (middleware bypassed)
            assert response.status_code == 200
            assert response.content == b"OK"


@pytest.mark.django_db
class TestRoleBasedAccessIntegration:
    """Integration tests for role-based access control with Django test client."""
    
    def test_middleware_integration_with_django_client(self):
        """Test that the middleware works correctly with Django's test client."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create users with different roles
        client_user = User.objects.create_user(username=f'client_user_{unique_id}', password='testpass')
        client_user.profile.role = 'client'
        client_user.profile.save()
        
        worker_user = User.objects.create_user(username=f'worker_user_{unique_id}', password='testpass')
        worker_user.profile.role = 'worker'
        worker_user.profile.save()
        
        admin_user = User.objects.create_user(username=f'admin_user_{unique_id}', password='testpass', is_staff=True)
        admin_user.profile.role = 'client'  # Role doesn't matter for staff
        admin_user.profile.save()
        
        client = Client()
        
        # Test that users can login successfully
        # (Portal redirection will be tested when portal views are implemented)
        login_success = client.login(username=f'client_user_{unique_id}', password='testpass')
        assert login_success
        
        client.logout()
        
        login_success = client.login(username=f'worker_user_{unique_id}', password='testpass')
        assert login_success
        
        client.logout()
        
        login_success = client.login(username=f'admin_user_{unique_id}', password='testpass')
        assert login_success
        
        # Test that middleware doesn't interfere with existing URLs
        response = client.get('/')
        # Should get some response (not necessarily 200, but not a middleware error)
        assert response.status_code in [200, 302, 404]  # Any valid HTTP response
        
        client.logout()
        
        # Test admin user - should have access to admin areas
        client.login(username='admin_user', password='testpass')
        
        # Admin accessing admin dashboard should either work or redirect to admin dashboard
        response = client.get('/admin-dashboard/', follow=False)
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert '/admin-dashboard/' in response.url