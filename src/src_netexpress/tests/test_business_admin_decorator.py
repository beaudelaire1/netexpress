"""
Tests for the business_admin_required decorator.

Validates that the decorator correctly allows access to:
- Users with is_staff=True
- Users belonging to the admin_business group
And blocks access for users without these permissions.
"""

import pytest
from django.contrib.auth.models import User, Group
from django.http import HttpResponse
from django.test import RequestFactory

from core.decorators import business_admin_required, is_business_admin


pytestmark = pytest.mark.django_db


class TestIsBusinessAdminFunction:
    """Tests for the is_business_admin helper function."""
    
    def test_unauthenticated_user_is_not_business_admin(self):
        """Unauthenticated users should not be considered business admins."""
        from django.contrib.auth.models import AnonymousUser
        user = AnonymousUser()
        assert is_business_admin(user) is False
    
    def test_staff_user_is_business_admin(self):
        """Users with is_staff=True should be considered business admins."""
        user = User.objects.create_user(
            username="staff_user",
            password="password123",
            is_staff=True
        )
        assert is_business_admin(user) is True
    
    def test_admin_business_group_member_is_business_admin(self):
        """Users in the admin_business group should be considered business admins."""
        user = User.objects.create_user(
            username="group_user",
            password="password123",
            is_staff=False
        )
        admin_business_group = Group.objects.create(name="admin_business")
        user.groups.add(admin_business_group)
        
        assert is_business_admin(user) is True
    
    def test_regular_user_is_not_business_admin(self):
        """Regular users without staff status or admin_business group should not be business admins."""
        user = User.objects.create_user(
            username="regular_user",
            password="password123",
            is_staff=False
        )
        assert is_business_admin(user) is False
    
    def test_user_in_other_group_is_not_business_admin(self):
        """Users in other groups (not admin_business) should not be business admins."""
        user = User.objects.create_user(
            username="other_group_user",
            password="password123",
            is_staff=False
        )
        other_group = Group.objects.create(name="other_group")
        user.groups.add(other_group)
        
        assert is_business_admin(user) is False


class TestBusinessAdminRequiredDecorator:
    """Tests for the @business_admin_required decorator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        
        # Create a simple view protected by the decorator
        @business_admin_required
        def protected_view(request):
            return HttpResponse("Success")
        
        self.protected_view = protected_view
    
    def test_staff_user_can_access_protected_view(self):
        """Staff users should be able to access views protected by @business_admin_required."""
        user = User.objects.create_user(
            username="staff_access",
            password="password123",
            is_staff=True
        )
        
        request = self.factory.get('/test/')
        request.user = user
        
        response = self.protected_view(request)
        assert response.status_code == 200
        assert response.content == b"Success"
    
    def test_admin_business_group_member_can_access_protected_view(self):
        """Users in admin_business group should be able to access protected views."""
        user = User.objects.create_user(
            username="group_access",
            password="password123",
            is_staff=False
        )
        admin_business_group = Group.objects.create(name="admin_business")
        user.groups.add(admin_business_group)
        
        request = self.factory.get('/test/')
        request.user = user
        
        response = self.protected_view(request)
        assert response.status_code == 200
        assert response.content == b"Success"
    
    def test_unauthenticated_user_is_redirected(self):
        """Unauthenticated users should be redirected to login."""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        response = self.protected_view(request)
        # user_passes_test redirects unauthenticated users to login
        assert response.status_code == 302
        assert '/admin/login/' in response.url
    
    def test_regular_user_is_redirected(self):
        """Regular users without permissions should be redirected to login."""
        user = User.objects.create_user(
            username="regular_access",
            password="password123",
            is_staff=False
        )
        
        request = self.factory.get('/test/')
        request.user = user
        
        response = self.protected_view(request)
        # user_passes_test redirects users who fail the test to login
        assert response.status_code == 302
        assert '/admin/login/' in response.url
    
    def test_superuser_can_access_protected_view(self):
        """Superusers (who have is_staff=True) should be able to access protected views."""
        user = User.objects.create_superuser(
            username="super_access",
            password="password123",
            email="super@test.com"
        )
        
        request = self.factory.get('/test/')
        request.user = user
        
        response = self.protected_view(request)
        assert response.status_code == 200
        assert response.content == b"Success"
