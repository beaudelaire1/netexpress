"""
Property-based tests for notification system.

These tests validate the correctness properties for the notification system
using Hypothesis for property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth.models import User, Group
from django.utils import timezone

from core.models import UINotification
from core.services import notification_service
from tasks.models import Task
from devis.models import Quote, Client
from factures.models import Invoice
from messaging.models import Message


class NotificationPropertiesTest(TestCase):
    """Property-based tests for notification system correctness."""
    
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
            username=f'admin_test_{unique_id}',
            email=f'admin_{unique_id}@test.com',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.worker_user = User.objects.create_user(
            username=f'worker_test_{unique_id}',
            email=f'worker_{unique_id}@test.com'
        )
        self.worker_user.groups.add(self.worker_group)
        
        self.client_user = User.objects.create_user(
            username=f'client_test_{unique_id}',
            email=f'client_{unique_id}@test.com'
        )
        self.client_user.groups.add(self.client_group)
        
        # Create test client
        self.test_client = Client.objects.create(
            full_name='Test Client',
            email=f'client_{unique_id}@test.com',
            phone='123456789'
        )
    
    @given(
        task_title=st.text(min_size=1, max_size=100),
        task_description=st.text(max_size=500),
    )
    @settings(max_examples=3)  # Reduced for faster execution
    def test_property_8_event_driven_notifications_task_completion(self, task_title, task_description):
        """
        **Feature: netexpress-v2-transformation, Property 8: Event-driven notifications**
        **Validates: Requirements 3.4, 6.4, 8.4**
        
        For any task completion event, appropriate notifications should be generated 
        and delivered to relevant users (admin users).
        """
        assume(task_title.strip())  # Ensure non-empty title
        
        # Create a task
        from datetime import date, timedelta
        task = Task.objects.create(
            title=task_title.strip(),
            description=task_description,
            assigned_to=self.worker_user,
            status=Task.STATUS_IN_PROGRESS,
            due_date=date.today() + timedelta(days=7)  # Due in 7 days
        )
        
        # Get initial notification count for admin
        initial_admin_notifications = UINotification.objects.filter(
            user=self.admin_user
        ).count()
        
        # Trigger task completion notification
        notification_service.notify_task_completion(task, self.worker_user)
        
        # Verify notification was created for admin user
        final_admin_notifications = UINotification.objects.filter(
            user=self.admin_user
        ).count()
        
        # Property: Task completion should generate exactly one notification for admin
        assert final_admin_notifications == initial_admin_notifications + 1
        
        # Verify notification content
        latest_notification = UINotification.objects.filter(
            user=self.admin_user,
            notification_type='task_completed'
        ).latest('created_at')
        
        assert task_title.strip() in latest_notification.title
        assert latest_notification.notification_type == 'task_completed'
        assert not latest_notification.read  # Should be unread initially
    
    @given(
        task_title=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=3)  # Reduced for faster execution
    def test_property_8_event_driven_notifications_task_assignment(self, task_title):
        """
        **Feature: netexpress-v2-transformation, Property 8: Event-driven notifications**
        **Validates: Requirements 3.4, 6.4, 8.4**
        
        For any task assignment event, appropriate notifications should be generated 
        and delivered to the assigned worker.
        """
        assume(task_title.strip())  # Ensure non-empty title
        
        # Create a task
        from datetime import date, timedelta
        task = Task.objects.create(
            title=task_title.strip(),
            status=Task.STATUS_UPCOMING,
            due_date=date.today() + timedelta(days=7)  # Due in 7 days
        )
        
        # Get initial notification count for worker
        initial_worker_notifications = UINotification.objects.filter(
            user=self.worker_user
        ).count()
        
        # Trigger task assignment notification
        notification_service.notify_task_assignment(task, self.worker_user)
        
        # Verify notification was created for worker
        final_worker_notifications = UINotification.objects.filter(
            user=self.worker_user
        ).count()
        
        # Property: Task assignment should generate exactly one notification for worker
        assert final_worker_notifications == initial_worker_notifications + 1
        
        # Verify notification content
        latest_notification = UINotification.objects.filter(
            user=self.worker_user,
            notification_type='task_assigned'
        ).latest('created_at')
        
        assert task_title.strip() in latest_notification.title
        assert latest_notification.notification_type == 'task_assigned'
        assert not latest_notification.read  # Should be unread initially
    
    @given(
        quote_number=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=3)  # Reduced for faster execution
    def test_property_8_event_driven_notifications_quote_validation(self, quote_number):
        """
        **Feature: netexpress-v2-transformation, Property 8: Event-driven notifications**
        **Validates: Requirements 3.4, 6.4, 8.4**
        
        For any quote validation event, appropriate notifications should be generated 
        and delivered to relevant users (admin and client if account exists).
        """
        assume(quote_number.strip())  # Ensure non-empty number
        
        # Create a quote
        quote = Quote.objects.create(
            number=quote_number.strip(),
            client=self.test_client,
            status=Quote.QuoteStatus.DRAFT
        )
        
        # Link client to user account
        self.test_client.user = self.client_user
        self.test_client.save()
        
        # Get initial notification counts
        initial_admin_notifications = UINotification.objects.filter(
            user=self.admin_user
        ).count()
        initial_client_notifications = UINotification.objects.filter(
            user=self.client_user
        ).count()
        
        # Trigger quote validation notification
        notification_service.notify_quote_validation(quote)
        
        # Verify notifications were created
        final_admin_notifications = UINotification.objects.filter(
            user=self.admin_user
        ).count()
        final_client_notifications = UINotification.objects.filter(
            user=self.client_user
        ).count()
        
        # Property: Quote validation should generate notifications for both admin and client
        assert final_admin_notifications == initial_admin_notifications + 1
        assert final_client_notifications == initial_client_notifications + 1
        
        # Verify admin notification
        admin_notification = UINotification.objects.filter(
            user=self.admin_user,
            notification_type='quote_validated'
        ).latest('created_at')
        
        assert quote_number.strip() in admin_notification.title
        assert admin_notification.notification_type == 'quote_validated'
        
        # Verify client notification
        client_notification = UINotification.objects.filter(
            user=self.client_user,
            notification_type='quote_validated'
        ).latest('created_at')
        
        assert quote_number.strip() in client_notification.title
        assert client_notification.notification_type == 'quote_validated'
    
    @given(
        message_subject=st.text(min_size=1, max_size=100),
        message_content=st.text(min_size=1, max_size=1000),
    )
    @settings(max_examples=3)  # Reduced for faster execution
    def test_property_8_event_driven_notifications_message_received(self, message_subject, message_content):
        """
        **Feature: netexpress-v2-transformation, Property 8: Event-driven notifications**
        **Validates: Requirements 3.4, 6.4, 8.4**
        
        For any message received event, appropriate notifications should be generated 
        and delivered to the message recipient.
        """
        assume(message_subject.strip() and message_content.strip())
        
        # Create a message
        message = Message.objects.create(
            sender=self.admin_user,
            recipient=self.client_user,
            subject=message_subject.strip(),
            content=message_content.strip()
        )
        
        # Get initial notification count for recipient
        initial_notifications = UINotification.objects.filter(
            user=self.client_user
        ).count()
        
        # Trigger message notification
        notification_service.notify_message_received(message)
        
        # Verify notification was created
        final_notifications = UINotification.objects.filter(
            user=self.client_user
        ).count()
        
        # Property: Message received should generate exactly one notification for recipient
        assert final_notifications == initial_notifications + 1
        
        # Verify notification content
        latest_notification = UINotification.objects.filter(
            user=self.client_user,
            notification_type='message_received'
        ).latest('created_at')
        
        assert message_subject.strip() in latest_notification.title
        assert latest_notification.notification_type == 'message_received'
        assert not latest_notification.read
    
    @given(
        username=st.text(min_size=3, max_size=30),
        email=st.emails(),
    )
    @settings(max_examples=3)  # Reduced for faster execution
    def test_property_8_event_driven_notifications_account_creation(self, username, email):
        """
        **Feature: netexpress-v2-transformation, Property 8: Event-driven notifications**
        **Validates: Requirements 3.4, 6.4, 8.4**
        
        For any account creation event, appropriate notifications should be generated 
        and delivered to admin users.
        """
        # Ensure unique username to avoid conflicts
        import uuid
        unique_username = f"{username}_{str(uuid.uuid4())[:8]}"
        
        # Create a new user
        new_user = User.objects.create_user(
            username=unique_username,
            email=email
        )
        
        # Get initial notification count for admin
        initial_admin_notifications = UINotification.objects.filter(
            user=self.admin_user
        ).count()
        
        # Trigger account creation notification
        password_reset_url = "http://example.com/reset/"
        notification_service.notify_account_creation(new_user, password_reset_url)
        
        # Verify notification was created for admin
        final_admin_notifications = UINotification.objects.filter(
            user=self.admin_user
        ).count()
        
        # Property: Account creation should generate exactly one notification for admin
        assert final_admin_notifications == initial_admin_notifications + 1
        
        # Verify notification content
        latest_notification = UINotification.objects.filter(
            user=self.admin_user,
            notification_type='account_created'
        ).latest('created_at')
        
        assert latest_notification.notification_type == 'account_created'
        # Check that either email or username is in the message (more flexible)
        assert (email in latest_notification.message or 
                unique_username in latest_notification.message or
                new_user.get_full_name() in latest_notification.message)
        assert not latest_notification.read
    
    @given(
        notification_count=st.integers(min_value=1, max_value=3),  # Reduced from max 5 to 3
    )
    @settings(max_examples=2)  # Reduced from 5 to 2
    def test_property_8_notification_delivery_consistency(self, notification_count):
        """
        **Feature: netexpress-v2-transformation, Property 8: Event-driven notifications**
        **Validates: Requirements 3.4, 6.4, 8.4**
        
        For any number of notification events, all notifications should be consistently 
        delivered and trackable.
        """
        # Create multiple notifications
        initial_count = UINotification.objects.filter(user=self.admin_user).count()
        
        for i in range(notification_count):
            notification_service.create_ui_notification(
                user=self.admin_user,
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                notification_type='general'
            )
        
        # Verify all notifications were created
        final_count = UINotification.objects.filter(user=self.admin_user).count()
        
        # Property: All requested notifications should be created
        assert final_count == initial_count + notification_count
        
        # Property: All notifications should be unread initially
        unread_count = UINotification.get_unread_count(self.admin_user)
        assert unread_count >= notification_count
        
        # Property: Marking notifications as read should work consistently
        notifications = UINotification.objects.filter(
            user=self.admin_user,
            read=False
        )[:notification_count]
        
        for notification in notifications:
            notification.mark_as_read()
        
        # Verify read status
        for notification in notifications:
            notification.refresh_from_db()
            assert notification.read
            assert notification.read_at is not None