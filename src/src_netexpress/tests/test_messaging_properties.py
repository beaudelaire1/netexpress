"""
Property-based tests for messaging system.

These tests validate universal properties that should hold across all valid inputs
for the messaging system, particularly focusing on WYSIWYG content preservation.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from messaging.models import Message, MessageThread
from messaging.forms import InternalMessageForm, MessageReplyForm


class MessagingPropertyTests(HypothesisTestCase):
    """Property-based tests for messaging functionality."""
    
    def setUp(self):
        """Set up test users for messaging tests."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        self.sender = User.objects.create_user(
            username=f'sender_{unique_id}',
            email=f'sender_{unique_id}@test.com',
            password='testpass123'
        )
        self.recipient = User.objects.create_user(
            username=f'recipient_{unique_id}', 
            email=f'recipient_{unique_id}@test.com',
            password='testpass123'
        )
    
    @given(
        subject=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        content=st.one_of([
            # Plain text content
            st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
            # HTML formatted content (common WYSIWYG patterns)
            st.sampled_from([
                '<p>Simple paragraph</p>',
                '<p><strong>Bold text</strong> and <em>italic text</em></p>',
                '<ul><li>Item 1</li><li>Item 2</li></ul>',
                '<ol><li>First</li><li>Second</li></ol>',
                '<p>Text with <a href="http://example.com">link</a></p>',
                '<p>Line 1<br>Line 2</p>',
                '<p><strong>Bold</strong> <em>italic</em> <u>underlined</u></p>',
                '<p>Mixed content with <strong>bold</strong> and <a href="#">links</a></p>',
            ]),
            # Combined text and HTML
            st.builds(
                lambda text, html: f'<p>{text}</p>{html}',
                st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
                st.sampled_from(['<p><strong>Bold</strong></p>', '<ul><li>List item</li></ul>'])
            )
        ])
    )
    def test_wysiwyg_content_preservation(self, subject, content):
        """
        **Feature: netexpress-v2-transformation, Property 5: WYSIWYG content preservation**
        
        For any rich text content created in the WYSIWYG editor, the content 
        displayed to recipients should preserve all formatting and match exactly 
        what was shown in the editor.
        
        **Validates: Requirements 5.3, 5.5**
        """
        # Create a message with the generated content
        message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject=subject,
            content=content
        )
        
        # Retrieve the message from database
        retrieved_message = Message.objects.get(id=message.id)
        
        # Property: Content should be preserved exactly as stored
        self.assertEqual(retrieved_message.content, content)
        
        # Property: Subject should be preserved exactly as stored
        self.assertEqual(retrieved_message.subject, subject)
        
        # Property: HTML content should remain valid HTML (no corruption)
        if '<' in content and '>' in content:
            # Basic HTML structure should be preserved
            self.assertIn('<', retrieved_message.content)
            self.assertIn('>', retrieved_message.content)
            
            # Common HTML tags should be preserved
            for tag in ['<p>', '<strong>', '<em>', '<ul>', '<li>', '<ol>', '<a', '<br>']:
                if tag in content:
                    self.assertIn(tag, retrieved_message.content)
    
    @given(
        original_content=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
        reply_content=st.text(min_size=1, max_size=500).filter(lambda x: x.strip())
    )
    def test_message_thread_content_preservation(self, original_content, reply_content):
        """
        Property test for message threading with content preservation.
        
        For any message thread, all messages in the thread should preserve
        their original content regardless of thread operations.
        """
        # Create original message
        original_message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject="Test Thread",
            content=original_content
        )
        
        # Create thread
        thread = MessageThread.objects.create(
            subject="Test Thread",
            last_message_at=original_message.created_at
        )
        thread.participants.add(self.sender, self.recipient)
        
        # Associate message with thread
        original_message.thread = thread
        original_message.save()
        
        # Create reply
        reply_message = Message.objects.create(
            sender=self.recipient,
            recipient=self.sender,
            subject=f"Re: {original_message.subject}",
            content=reply_content,
            thread=thread
        )
        
        # Retrieve messages from thread
        thread_messages = thread.messages.all().order_by('created_at')
        
        # Property: All messages in thread should preserve their content
        self.assertEqual(len(thread_messages), 2)
        self.assertEqual(thread_messages[0].content, original_content)
        self.assertEqual(thread_messages[1].content, reply_content)
        
        # Property: Thread should maintain correct participant relationships
        self.assertIn(self.sender, thread.participants.all())
        self.assertIn(self.recipient, thread.participants.all())
    
    @settings(deadline=None, max_examples=15)
    @given(
        content=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'), min_codepoint=32, max_codepoint=126)).filter(lambda x: x.strip())
    )
    def test_form_content_preservation(self, content):
        """
        Property test for form handling of WYSIWYG content.
        
        For any content submitted through messaging forms, the content
        should be preserved with appropriate normalization (trimmed whitespace).
        Forms typically normalize user input by trimming leading/trailing whitespace.
        """
        # Test InternalMessageForm
        form_data = {
            'recipient': self.recipient.id,
            'subject': 'Test Subject',
            'content': content
        }
        
        form = InternalMessageForm(data=form_data, sender=self.sender)
        
        # Property: Form should be valid for any non-empty content
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        # Property: Saved message should preserve content (with normalization)
        message = form.save()
        # Forms may normalize whitespace, so we compare the normalized versions
        self.assertEqual(message.content.strip(), content.strip())
        
        # Property: Content should survive database round-trip
        retrieved_message = Message.objects.get(id=message.id)
        self.assertEqual(retrieved_message.content.strip(), content.strip())
    
    @given(
        content=st.one_of([
            st.text(min_size=1, max_size=500),
            st.sampled_from([
                '<script>alert("xss")</script>',  # Should be handled safely
                '<p>Normal content</p>',
                '&lt;script&gt;safe&lt;/script&gt;',  # Already escaped
                '<p>Content with "quotes" and \'apostrophes\'</p>',
                '<p>Unicode: café, naïve, résumé</p>',
            ])
        ])
    )
    def test_content_safety_preservation(self, content):
        """
        Property test for content safety while preserving formatting.
        
        For any content (including potentially unsafe content), the system
        should preserve the content while maintaining security.
        """
        message = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject="Safety Test",
            content=content
        )
        
        # Property: Content should be stored exactly as provided
        # (Security filtering should happen at display time, not storage)
        retrieved_message = Message.objects.get(id=message.id)
        self.assertEqual(retrieved_message.content, content)
        
        # Property: Message should be retrievable and valid
        self.assertIsNotNone(retrieved_message.sender)
        self.assertIsNotNone(retrieved_message.recipient)
        self.assertIsNotNone(retrieved_message.created_at)