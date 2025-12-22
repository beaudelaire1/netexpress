"""
Property-based tests for dynamic UI updates.

These tests validate the correctness properties for dynamic UI updates
using Hypothesis for property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.extra.django import TestCase
from django.test import Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone

from core.models import UINotification
from core.services import notification_service


class DynamicUIPropertiesTest(TestCase):
    """Property-based tests for dynamic UI updates correctness."""
    
    def setUp(self):
        """Set up test data."""
        # Create groups (use get_or_create to avoid unique constraint errors)
        self.admin_group, _ = Group.objects.get_or_create(name='Administrators')
        self.worker_group, _ = Group.objects.get_or_create(name='Workers')
        self.client_group, _ = Group.objects.get_or_create(name='Clients')
        
        # Create test users with unique usernames
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        self.admin_user = User.objects.create_user(
            username=f'admin_test_ui_{unique_id}',
            email='admin@test.com',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.worker_user = User.objects.create_user(
            username=f'worker_test_ui_{unique_id}',
            email='worker@test.com'
        )
        self.worker_user.groups.add(self.worker_group)
        
        self.client_user = User.objects.create_user(
            username=f'client_test_ui_{unique_id}',
            email='client@test.com'
        )
        self.client_user.groups.add(self.client_group)
        
        # Create test client for HTTP requests
        self.test_client = Client()
    
    @given(
        notification_title=st.text(min_size=1, max_size=100),
        notification_message=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=5, deadline=None)  # Disabled deadline for UI tests
    def test_property_9_dynamic_ui_updates_notification_count(self, notification_title, notification_message):
        """
        **Feature: netexpress-v2-transformation, Property 9: Dynamic UI updates**
        **Validates: Requirements 8.3**
        
        For any notification creation, the notification count endpoint should 
        dynamically reflect the updated count without requiring a full page reload.
        """
        assume(notification_title.strip() and notification_message.strip())
        
        # Login as admin user
        self.test_client.force_login(self.admin_user)
        
        # Get initial notification count via HTMX endpoint
        initial_response = self.test_client.get(reverse('core:notification_count'))
        assert initial_response.status_code == 200
        initial_count_html = initial_response.content.decode()
        
        # Create a new notification
        notification_service.create_ui_notification(
            user=self.admin_user,
            title=notification_title.strip(),
            message=notification_message.strip(),
            notification_type='general'
        )
        
        # Get updated notification count via HTMX endpoint
        updated_response = self.test_client.get(reverse('core:notification_count'))
        assert updated_response.status_code == 200
        updated_count_html = updated_response.content.decode()
        
        # Property: The notification count should be dynamically updated
        # The HTML content should change to reflect the new notification
        assert updated_count_html != initial_count_html or initial_count_html == ""
        
        # Verify the count is actually higher (if there was an initial count)
        if initial_count_html.strip() and initial_count_html.strip().isdigit():
            initial_count = int(initial_count_html.strip())
            if updated_count_html.strip().isdigit():
                updated_count = int(updated_count_html.strip())
                assert updated_count > initial_count
    
    @given(
        notification_count=st.integers(min_value=1, max_value=3),  # Small number for faster tests
    )
    @settings(max_examples=3, deadline=None)  # Disabled deadline for UI tests
    def test_property_9_dynamic_ui_updates_notification_list(self, notification_count):
        """
        **Feature: netexpress-v2-transformation, Property 9: Dynamic UI updates**
        **Validates: Requirements 8.3**
        
        For any number of notifications, the notification list endpoint should 
        dynamically return the updated list without requiring a full page reload.
        """
        # Login as admin user
        self.test_client.force_login(self.admin_user)
        
        # Get initial notification list via HTMX endpoint
        initial_response = self.test_client.get(reverse('core:notification_list'))
        assert initial_response.status_code == 200
        initial_list_html = initial_response.content.decode()
        
        # Create multiple notifications
        created_notifications = []
        for i in range(notification_count):
            notification = notification_service.create_ui_notification(
                user=self.admin_user,
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                notification_type='general'
            )
            created_notifications.append(notification)
        
        # Get updated notification list via HTMX endpoint
        updated_response = self.test_client.get(reverse('core:notification_list'))
        assert updated_response.status_code == 200
        updated_list_html = updated_response.content.decode()
        
        # Property: The notification list should be dynamically updated
        # The HTML content should change to include the new notifications
        assert updated_list_html != initial_list_html
        
        # Verify all created notifications appear in the updated list
        for notification in created_notifications:
            assert notification.title in updated_list_html
    
    @given(
        notification_title=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=3, deadline=None)  # Disabled deadline for UI tests
    def test_property_9_dynamic_ui_updates_mark_as_read(self, notification_title):
        """
        **Feature: netexpress-v2-transformation, Property 9: Dynamic UI updates**
        **Validates: Requirements 8.3**
        
        For any notification that is marked as read, the UI should dynamically 
        update to reflect the read status without requiring a full page reload.
        """
        assume(notification_title.strip())
        
        # Login as admin user
        self.test_client.force_login(self.admin_user)
        
        # Create a notification
        notification = notification_service.create_ui_notification(
            user=self.admin_user,
            title=notification_title.strip(),
            message="Test message for read status",
            notification_type='general'
        )
        
        # Verify notification is initially unread
        assert not notification.read
        
        # Get initial notification list
        initial_response = self.test_client.get(reverse('core:notification_list'))
        assert initial_response.status_code == 200
        initial_list_html = initial_response.content.decode()
        
        # Mark notification as read via HTMX endpoint
        mark_read_response = self.test_client.post(
            reverse('core:mark_notification_read', args=[notification.id])
        )
        assert mark_read_response.status_code == 200
        updated_list_html = mark_read_response.content.decode()
        
        # Property: The UI should dynamically update to show the read status
        # The HTML content should change to reflect the notification is now read
        assert updated_list_html != initial_list_html
        
        # Verify the notification is actually marked as read in the database
        notification.refresh_from_db()
        assert notification.read
        assert notification.read_at is not None
    
    def test_property_9_dynamic_ui_updates_mark_all_read(self):
        """
        **Feature: netexpress-v2-transformation, Property 9: Dynamic UI updates**
        **Validates: Requirements 8.3**
        
        For any "mark all as read" action, the UI should dynamically update 
        to reflect that all notifications are read without requiring a full page reload.
        """
        # Login as admin user
        self.test_client.force_login(self.admin_user)
        
        # Create multiple notifications
        notifications = []
        for i in range(3):
            notification = notification_service.create_ui_notification(
                user=self.admin_user,
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                notification_type='general'
            )
            notifications.append(notification)
        
        # Verify all notifications are initially unread
        for notification in notifications:
            assert not notification.read
        
        # Get initial notification list
        initial_response = self.test_client.get(reverse('core:notification_list'))
        assert initial_response.status_code == 200
        initial_list_html = initial_response.content.decode()
        
        # Mark all notifications as read via HTMX endpoint
        mark_all_read_response = self.test_client.post(
            reverse('core:mark_all_notifications_read')
        )
        assert mark_all_read_response.status_code == 200
        updated_list_html = mark_all_read_response.content.decode()
        
        # Property: The UI should dynamically update to show all notifications as read
        # The HTML content should change to reflect the new read status
        assert updated_list_html != initial_list_html
        
        # Verify all notifications are actually marked as read in the database
        for notification in notifications:
            notification.refresh_from_db()
            assert notification.read
            assert notification.read_at is not None
    
    @given(
        user_type=st.sampled_from(['admin', 'worker', 'client']),
    )
    @settings(max_examples=3, deadline=None)  # Disabled deadline for UI tests
    def test_property_9_dynamic_ui_updates_user_specific_content(self, user_type):
        """
        **Feature: netexpress-v2-transformation, Property 9: Dynamic UI updates**
        **Validates: Requirements 8.3**
        
        For any user type, the notification endpoints should dynamically return 
        content specific to that user without affecting other users' content.
        """
        # Select user based on type
        if user_type == 'admin':
            test_user = self.admin_user
        elif user_type == 'worker':
            test_user = self.worker_user
        else:
            test_user = self.client_user
        
        # Login as the selected user
        self.test_client.force_login(test_user)
        
        # Create a notification for this specific user
        notification = notification_service.create_ui_notification(
            user=test_user,
            title=f"Notification for {user_type}",
            message=f"This is a message for {user_type} user",
            notification_type='general'
        )
        
        # Get notification count for this user
        count_response = self.test_client.get(reverse('core:notification_count'))
        assert count_response.status_code == 200
        count_html = count_response.content.decode()
        
        # Get notification list for this user
        list_response = self.test_client.get(reverse('core:notification_list'))
        assert list_response.status_code == 200
        list_html = list_response.content.decode()
        
        # Property: The user should see their own notifications
        assert notification.title in list_html
        
        # Property: The count should reflect this user's notifications
        # (At minimum, should show the notification we just created)
        if count_html.strip() and count_html.strip().isdigit():
            count = int(count_html.strip())
            assert count >= 1
        
        # Verify other users don't see this notification
        other_users = [u for u in [self.admin_user, self.worker_user, self.client_user] if u != test_user]
        for other_user in other_users:
            other_notifications = UINotification.objects.filter(user=other_user)
            assert notification not in other_notifications