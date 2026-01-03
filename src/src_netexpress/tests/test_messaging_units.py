"""
Unit tests for messaging system functionality.

These tests validate specific examples and edge cases for the messaging system,
focusing on message creation, threading, and CKEditor integration.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from messaging.models import Message, MessageThread
from messaging.forms import InternalMessageForm, MessageReplyForm


class MessageModelTests(TestCase):
    """Unit tests for Message model functionality."""
    
    def setUp(self):
        """Set up test users and data."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.recipient = User.objects.create_user(
            username='recipient',
            email='recipient@test.com',
            password='testpass123'
        )
    
    def test_message_creation(self):
        """Test basic message creation and properties."""
        message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Test Subject',
            content='<p>Test content with <strong>formatting</strong></p>'
        )
        
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.recipient, self.recipient)
        self.assertEqual(message.subject, 'Test Subject')
        self.assertIn('<strong>formatting</strong>', message.content)
        self.assertIsNotNone(message.created_at)
        self.assertIsNone(message.read_at)
        self.assertFalse(message.is_read)
    
    def test_message_mark_as_read(self):
        """Test marking message as read functionality."""
        message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Test Subject',
            content='Test content'
        )
        
        # Initially unread
        self.assertFalse(message.is_read)
        self.assertIsNone(message.read_at)
        
        # Mark as read
        message.mark_as_read()
        
        # Should be marked as read
        self.assertTrue(message.is_read)
        self.assertIsNotNone(message.read_at)
        
        # Marking as read again should not change timestamp
        original_read_at = message.read_at
        message.mark_as_read()
        self.assertEqual(message.read_at, original_read_at)
    
    def test_message_string_representation(self):
        """Test message string representation."""
        message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Test Subject',
            content='Test content'
        )
        
        expected = f"Test Subject - {self.sender.username} → {self.recipient.username}"
        self.assertEqual(str(message), expected)


class MessageThreadModelTests(TestCase):
    """Unit tests for MessageThread model functionality."""
    
    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
    
    def test_thread_creation(self):
        """Test message thread creation."""
        thread = MessageThread.objects.create(
            subject='Test Thread'
        )
        thread.participants.add(self.user1, self.user2)
        
        self.assertEqual(thread.subject, 'Test Thread')
        self.assertEqual(thread.participants.count(), 2)
        self.assertIn(self.user1, thread.participants.all())
        self.assertIn(self.user2, thread.participants.all())
    
    def test_thread_string_representation(self):
        """Test thread string representation."""
        thread = MessageThread.objects.create(
            subject='Test Thread'
        )
        thread.participants.add(self.user1, self.user2)
        
        expected = "Test Thread (2 participants)"
        self.assertEqual(str(thread), expected)


class InternalMessageFormTests(TestCase):
    """Unit tests for InternalMessageForm."""
    
    def setUp(self):
        """Set up test users."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.recipient = User.objects.create_user(
            username='recipient',
            email='recipient@test.com',
            password='testpass123'
        )
    
    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'recipient': self.recipient.id,
            'subject_type': 'question',
            'reference': 'Devis #123',
            'content': '<p>Test content with <strong>formatting</strong></p>'
        }
        
        form = InternalMessageForm(data=form_data, sender=self.sender)
        self.assertTrue(form.is_valid())
        
        message = form.save()
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.recipient, self.recipient)
        self.assertEqual(message.subject, 'Question — Devis #123')
        self.assertIn('<strong>formatting</strong>', message.content)
    
    def test_form_creates_thread(self):
        """Test that form creates message thread."""
        form_data = {
            'recipient': self.recipient.id,
            'subject_type': 'suivi_devis',
            'reference': 'Test #456',
            'content': 'Test content'
        }
        
        form = InternalMessageForm(data=form_data, sender=self.sender)
        self.assertTrue(form.is_valid())
        
        message = form.save()
        
        # Should create a thread
        self.assertIsNotNone(message.thread)
        self.assertEqual(message.thread.subject, 'Suivi de devis — Test #456')
        self.assertIn(self.sender, message.thread.participants.all())
        self.assertIn(self.recipient, message.thread.participants.all())
    
    def test_form_excludes_sender_from_recipients(self):
        """Test that sender is excluded from recipient choices."""
        form = InternalMessageForm(sender=self.sender)
        
        recipient_choices = list(form.fields['recipient'].queryset.values_list('id', flat=True))
        self.assertNotIn(self.sender.id, recipient_choices)
        self.assertIn(self.recipient.id, recipient_choices)
    
    def test_form_invalid_data(self):
        """Test form with invalid data."""
        # Missing required fields
        form_data = {
            'subject_type': 'question'
            # Missing recipient and content
        }
        
        form = InternalMessageForm(data=form_data, sender=self.sender)
        self.assertFalse(form.is_valid())
        self.assertIn('recipient', form.errors)
        self.assertIn('content', form.errors)


class MessageReplyFormTests(TestCase):
    """Unit tests for MessageReplyForm."""
    
    def setUp(self):
        """Set up test users and original message."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.recipient = User.objects.create_user(
            username='recipient',
            email='recipient@test.com',
            password='testpass123'
        )
        
        # Create original message with thread
        self.thread = MessageThread.objects.create(
            subject='Original Subject'
        )
        self.thread.participants.add(self.sender, self.recipient)
        
        self.original_message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Original Subject',
            content='Original content',
            thread=self.thread
        )
    
    def test_reply_form_valid_data(self):
        """Test reply form with valid data."""
        form_data = {
            'content': '<p>This is a reply with <em>formatting</em></p>'
        }
        
        form = MessageReplyForm(
            data=form_data,
            sender=self.recipient,
            original_message=self.original_message
        )
        
        self.assertTrue(form.is_valid())
        
        reply = form.save()
        self.assertEqual(reply.sender, self.recipient)
        self.assertEqual(reply.recipient, self.sender)
        self.assertEqual(reply.subject, 'Re: Original Subject')
        self.assertEqual(reply.thread, self.thread)
        self.assertIn('<em>formatting</em>', reply.content)
    
    def test_reply_updates_thread_timestamp(self):
        """Test that reply updates thread's last_message_at."""
        original_timestamp = self.thread.last_message_at
        
        form_data = {
            'content': 'Reply content'
        }
        
        form = MessageReplyForm(
            data=form_data,
            sender=self.recipient,
            original_message=self.original_message
        )
        
        reply = form.save()
        
        # Refresh thread from database
        self.thread.refresh_from_db()
        
        # Thread timestamp should be updated
        self.assertGreater(self.thread.last_message_at, original_timestamp)
        self.assertEqual(self.thread.last_message_at, reply.created_at)


class MessagingViewTests(TestCase):
    """Unit tests for messaging views."""
    
    def setUp(self):
        """Set up test users and client."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.recipient = User.objects.create_user(
            username='recipient',
            email='recipient@test.com',
            password='testpass123'
        )
        self.client = Client()
    
    def test_internal_message_list_requires_login(self):
        """Test that message list requires authentication."""
        url = reverse('messaging:internal_list')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_internal_message_list_authenticated(self):
        """Test message list view for authenticated user."""
        self.client.login(username='sender', password='testpass123')
        
        # Create a message
        Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Test Message',
            content='Test content'
        )
        
        url = reverse('messaging:internal_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Message')
        self.assertContains(response, 'Messages internes')
    
    def test_internal_message_compose_get(self):
        """Test message compose view GET request."""
        self.client.login(username='sender', password='testpass123')
        
        url = reverse('messaging:internal_compose')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nouveau message')
        self.assertContains(response, 'form')
    
    def test_internal_message_compose_post(self):
        """Test message compose view POST request."""
        self.client.login(username='sender', password='testpass123')
        
        url = reverse('messaging:internal_compose')
        form_data = {
            'recipient': self.recipient.id,
            'subject_type': 'information',
            'reference': '',
            'content': '<p>Test content</p>'
        }
        
        response = self.client.post(url, form_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Message should be created
        message = Message.objects.get(subject='Information')
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.recipient, self.recipient)
    
    def test_message_detail_marks_as_read(self):
        """Test that viewing message detail marks it as read for recipient."""
        message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Test Message',
            content='Test content'
        )
        
        # Login as recipient
        self.client.login(username='recipient', password='testpass123')
        
        # Initially unread
        self.assertFalse(message.is_read)
        
        # View message detail
        url = reverse('messaging:internal_detail', args=[message.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Message should now be marked as read
        message.refresh_from_db()
        self.assertTrue(message.is_read)
    
    def test_message_detail_access_control(self):
        """Test that users can only access their own messages."""
        # Create a third user
        other_user = User.objects.create_user(
            username='other',
            email='other@test.com',
            password='testpass123'
        )
        
        message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject='Private Message',
            content='Private content'
        )
        
        # Login as other user (not sender or recipient)
        self.client.login(username='other', password='testpass123')
        
        url = reverse('messaging:internal_detail', args=[message.id])
        response = self.client.get(url)
        
        # Should return 404 (not found) for unauthorized access
        self.assertEqual(response.status_code, 404)


class MessageContentTests(TestCase):
    """Unit tests for message content handling."""
    
    def setUp(self):
        """Set up test users."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@test.com',
            password='testpass123'
        )
        self.recipient = User.objects.create_user(
            username='recipient',
            email='recipient@test.com',
            password='testpass123'
        )
    
    def test_message_content_handling(self):
        """Test that message content is properly handled."""
        # Test various content formats
        test_contents = [
            'Simple text message',
            'Message with\nmultiple lines',
            'Message with special chars: é à ü ñ',
            'Message with numbers: 12345',
        ]
        
        for content in test_contents:
            with self.subTest(content=content):
                message = Message.objects.create(
                    sender=self.sender,
                    recipient=self.recipient,
                    subject='Content Test',
                    content=content
                )
                
                # Content should be preserved exactly
                self.assertEqual(message.content, content)
                
                # Should survive database round-trip
                retrieved = Message.objects.get(id=message.id)
                self.assertEqual(retrieved.content, content)
    
    def test_form_widget_configuration(self):
        """Test that content field uses TinyMCE widget."""
        form = InternalMessageForm(sender=self.sender)
        
        # Check that content field uses TinyMCE
        content_widget = form.fields['content'].widget
        self.assertEqual(content_widget.__class__.__name__, 'TinyMCE')