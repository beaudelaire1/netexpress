"""
Integration tests for factures views with business_admin_required decorator.

Validates that invoice views correctly use the business_admin_required decorator
and allow access to both staff users and admin_business group members.
"""

import pytest
from django.contrib.auth.models import User, Group
from django.urls import reverse


pytestmark = pytest.mark.django_db


class TestFacturesViewsAccessControl:
    """Integration tests for invoice views access control."""
    
    def test_staff_user_can_access_archive_view(self, client):
        """Staff users should be able to access the invoice archive view."""
        # Create staff user
        staff_user = User.objects.create_user(
            username="staff_invoice",
            password="password123",
            is_staff=True
        )
        
        # Login and access archive
        client.login(username="staff_invoice", password="password123")
        response = client.get(reverse("factures:archive"))
        
        # Should be successful (200)
        assert response.status_code == 200
    
    def test_admin_business_group_member_can_access_archive_view(self, client):
        """Users in admin_business group should be able to access the invoice archive view."""
        # Create user and add to admin_business group
        user = User.objects.create_user(
            username="business_admin_invoice",
            password="password123",
            is_staff=False
        )
        admin_business_group = Group.objects.create(name="admin_business")
        user.groups.add(admin_business_group)
        
        # Create profile with admin_business role
        # The middleware and role system requires a profile with explicit role
        from accounts.models import Profile
        Profile.objects.update_or_create(
            user=user,
            defaults={'role': 'admin_business'}
        )
        
        # Login and access archive
        client.login(username="business_admin_invoice", password="password123")
        response = client.get(reverse("factures:archive"))
        
        # Should be successful (200)
        assert response.status_code == 200
    
    def test_regular_user_cannot_access_archive_view(self, client):
        """Regular users without permissions should not be able to access the invoice archive view."""
        # Create regular user without permissions
        user = User.objects.create_user(
            username="regular_invoice",
            password="password123",
            is_staff=False
        )
        
        # Login and try to access archive
        client.login(username="regular_invoice", password="password123")
        response = client.get(reverse("factures:archive"), follow=False)
        
        # Should be redirected (302) - either to login or to their appropriate portal
        assert response.status_code == 302
        # The user is redirected away from the factures view because they don't have permission
        assert response.url in ['/admin/login/', '/client/']
    
    def test_unauthenticated_user_cannot_access_archive_view(self, client):
        """Unauthenticated users should be redirected to login."""
        response = client.get(reverse("factures:archive"))
        
        # Should be redirected to login
        assert response.status_code == 302
        # First decorator is @login_required which redirects to /accounts/login/
        assert '/login' in response.url
