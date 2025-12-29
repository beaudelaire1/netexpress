"""
Integration tests for complete user workflows across all portals.

Tests end-to-end scenarios:
- Client workflow: login → view documents → send message
- Worker workflow: login → view tasks → complete task  
- Admin workflow: login → view KPIs → validate document

These tests validate the complete user experience and integration
between all system components.
"""

import pytest
from django.test import TestCase, Client as DjangoTestClient
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import Profile
from devis.models import Quote, QuoteItem, Client
from factures.models import Invoice, InvoiceItem
from tasks.models import Task
from messaging.models import Message, MessageThread
from core.models import UINotification, PortalSession
from core.services.notification_service import NotificationService


class BaseWorkflowTest(TestCase):
    """Base class for workflow tests with common setup."""
    
    def setUp(self):
        """Set up test data common to all workflows."""
        # Create groups
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        self.client_user = User.objects.create_user(
            username='client1',
            email='client1@test.com',
            password='testpass123',
            first_name='Jean',
            last_name='Dupont'
        )
        
        self.worker_user = User.objects.create_user(
            username='worker1',
            email='worker1@test.com',
            password='testpass123',
            first_name='Pierre',
            last_name='Martin'
        )
        
        # Create or get profiles (in case they're created by signals)
        client_profile, _ = Profile.objects.get_or_create(
            user=self.client_user,
            defaults={'role': 'client'}
        )
        worker_profile, _ = Profile.objects.get_or_create(
            user=self.worker_user,
            defaults={'role': 'worker'}
        )
        
        # Ensure correct roles
        client_profile.role = 'client'
        client_profile.save()
        worker_profile.role = 'worker'
        worker_profile.save()
        
        # Add users to groups
        self.client_user.groups.add(self.clients_group)
        self.worker_user.groups.add(self.workers_group)
        
        # Create test client
        self.test_client = DjangoTestClient()


@pytest.mark.django_db
class TestClientWorkflow(BaseWorkflowTest):
    """Test complete client workflow: login → view documents → send message."""
    
    def setUp(self):
        super().setUp()
        
        # Create test client (devis.Client, not User)
        self.devis_client = Client.objects.create(
            full_name='Jean Dupont',
            email='client1@test.com',
            phone='0594123456',
            address_line='123 Rue de la Paix',
            city='Cayenne',
            zip_code='97300'
        )
        
        # Create test quote for client
        self.quote = Quote.objects.create(
            client=self.devis_client,
            number='Q2024-001',
            status='validated',
            total_ttc=1500.00,
            created_at=timezone.now() - timedelta(days=5)
        )
        
        # Create quote item
        QuoteItem.objects.create(
            quote=self.quote,
            description='Nettoyage bureau',
            quantity=1,
            unit_price=1500.00
        )
        
        # Create test invoice for client (linked through quote)
        self.invoice = Invoice.objects.create(
            quote=self.quote,
            number='F2024-001',
            status='sent',
            total_ttc=1500.00,
            due_date=timezone.now() + timedelta(days=30)
        )
        
        # Create invoice item
        InvoiceItem.objects.create(
            invoice=self.invoice,
            description='Nettoyage bureau',
            quantity=1,
            unit_price=1500.00
        )
    
    def test_complete_client_workflow(self):
        """Test the complete client workflow from login to message sending."""
        
        # Step 1: Client logs in
        login_successful = self.test_client.login(
            username='client1',
            password='testpass123'
        )
        self.assertTrue(login_successful, "Client should be able to log in")
        
        # Step 2: Client is redirected to their portal
        response = self.test_client.get('/')
        # Should redirect to client portal or show client-specific content
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Client accesses their dashboard
        response = self.test_client.get('/client/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Client', msg_prefix="Should show client dashboard")
        
        # Step 4: Client views their quotes
        response = self.test_client.get('/client/quotes/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Q2024-001', msg_prefix="Should show client's quote")
        self.assertContains(response, '1500', msg_prefix="Should show quote amount")
        
        # Step 5: Client views quote detail
        response = self.test_client.get(f'/client/quotes/{self.quote.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nettoyage bureau', msg_prefix="Should show quote details")
        
        # Step 6: Client views their invoices
        response = self.test_client.get('/client/invoices/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'F2024-001', msg_prefix="Should show client's invoice")
        
        # Step 7: Client views invoice detail
        response = self.test_client.get(f'/client/invoices/{self.invoice.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'F2024-001', msg_prefix="Should show invoice details")
        
        # Step 8: Client accesses messaging
        response = self.test_client.get('/client/messages/')
        if response.status_code == 302:
            print(f"Redirected to: {response.url}")
            print(f"User role: {getattr(self.client_user.profile, 'role', 'No profile')}")
            print(f"User groups: {list(self.client_user.groups.values_list('name', flat=True))}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Messages', msg_prefix="Should show messaging interface")
        
        # Step 9: Client composes a message
        response = self.test_client.get('/client/messages/compose/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nouveau message', msg_prefix="Should show compose form")
        
        # Step 10: Client sends a message
        message_data = {
            'recipient': self.admin_user.id,
            'subject': 'Question sur ma facture',
            'content': '<p>Bonjour, j\'ai une question concernant ma facture F2024-001.</p>'
        }
        response = self.test_client.post('/client/messages/compose/', message_data)
        
        # Should redirect after successful message creation
        self.assertIn(response.status_code, [200, 302])
        
        # Verify message was created
        message_exists = Message.objects.filter(
            sender=self.client_user,
            recipient=self.admin_user,
            subject='Question sur ma facture'
        ).exists()
        self.assertTrue(message_exists, "Message should be created")
        
        # Step 11: Verify client can access their sent messages
        response = self.test_client.get('/client/messages/')
        self.assertEqual(response.status_code, 200)
        
        # Step 12: Client logs out
        response = self.test_client.post('/accounts/logout/')
        self.assertIn(response.status_code, [200, 302])


@pytest.mark.django_db
class TestWorkerWorkflow(BaseWorkflowTest):
    """Test complete worker workflow: login → view tasks → complete task."""
    
    def setUp(self):
        super().setUp()
        
        # Create test task for worker
        self.task = Task.objects.create(
            title='Nettoyage Bureau ABC',
            description='Nettoyage complet des bureaux',
            location='123 Rue de la Paix, Cayenne',
            assigned_to=self.worker_user,
            status=Task.STATUS_UPCOMING,
            start_date=timezone.now().date() + timedelta(days=1),
            due_date=timezone.now().date() + timedelta(days=2)
        )
        
        # Create another task for different day
        self.task2 = Task.objects.create(
            title='Entretien Jardin XYZ',
            description='Taille des haies et tonte',
            location='456 Avenue des Palmiers, Matoury',
            assigned_to=self.worker_user,
            status=Task.STATUS_UPCOMING,
            start_date=timezone.now().date() + timedelta(days=2),
            due_date=timezone.now().date() + timedelta(days=3)
        )
    
    def test_complete_worker_workflow(self):
        """Test the complete worker workflow from login to task completion."""
        
        # Step 1: Worker logs in
        login_successful = self.test_client.login(
            username='worker1',
            password='testpass123'
        )
        self.assertTrue(login_successful, "Worker should be able to log in")
        
        # Step 2: Worker accesses their dashboard
        response = self.test_client.get('/worker/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Worker', msg_prefix="Should show worker dashboard")
        self.assertContains(response, 'Nettoyage Bureau ABC', msg_prefix="Should show assigned task")
        
        # Step 3: Worker views their schedule
        response = self.test_client.get('/worker/schedule/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planning', msg_prefix="Should show schedule view")
        self.assertContains(response, 'Nettoyage Bureau ABC', msg_prefix="Should show task in schedule")
        
        # Step 4: Worker views task details
        response = self.test_client.get(f'/worker/tasks/{self.task.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nettoyage Bureau ABC', msg_prefix="Should show task details")
        self.assertContains(response, '123 Rue de la Paix', msg_prefix="Should show task location")
        
        # Step 5: Worker marks task as in progress
        response = self.test_client.post(f'/worker/tasks/{self.task.id}/start/')
        self.assertIn(response.status_code, [200, 302])
        
        # Verify task status changed
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'in_progress', "Task should be marked as in progress")
        
        # Step 6: Worker completes the task
        completion_data = {
            'completion_notes': 'Tâche terminée avec succès. Bureaux nettoyés et désinfectés.',
            'status': 'completed'
        }
        response = self.test_client.post(f'/worker/tasks/{self.task.id}/complete/', completion_data)
        self.assertIn(response.status_code, [200, 302])
        
        # Verify task completion
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'completed', "Task should be marked as completed")
        self.assertEqual(self.task.completed_by, self.worker_user, "Task should be completed by worker")
        self.assertIsNotNone(self.task.completed_at, "Task should have completion timestamp")
        
        # Step 7: Verify notification was created for admin
        notification_exists = UINotification.objects.filter(
            user=self.admin_user,
            notification_type='task_completed',
            message__icontains='Nettoyage Bureau ABC'
        ).exists()
        self.assertTrue(notification_exists, "Admin should receive task completion notification")
        
        # Step 8: Worker accesses messaging
        response = self.test_client.get('/worker/messages/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Messages', msg_prefix="Should show messaging interface")
        
        # Step 9: Worker sends a message about task completion
        message_data = {
            'recipient': self.admin_user.id,
            'subject': 'Tâche terminée - Nettoyage Bureau ABC',
            'content': '<p>La tâche de nettoyage a été terminée avec succès.</p>'
        }
        response = self.test_client.post('/worker/messages/compose/', message_data)
        self.assertIn(response.status_code, [200, 302])
        
        # Verify message was created
        message_exists = Message.objects.filter(
            sender=self.worker_user,
            recipient=self.admin_user,
            subject__icontains='Tâche terminée'
        ).exists()
        self.assertTrue(message_exists, "Message should be created")
        
        # Step 10: Worker logs out
        response = self.test_client.post('/accounts/logout/')
        self.assertIn(response.status_code, [200, 302])


@pytest.mark.django_db
class TestAdminWorkflow(BaseWorkflowTest):
    """Test complete admin workflow: login → view KPIs → validate document."""
    
    def setUp(self):
        super().setUp()
        
        # Create test client (devis.Client)
        self.devis_client = Client.objects.create(
            full_name='Jean Dupont',
            email='client1@test.com',
            phone='0594123456',
            address_line='123 Rue de la Paix',
            city='Cayenne',
            zip_code='97300'
        )
        
        # Create test quote for validation
        self.quote = Quote.objects.create(
            client=self.devis_client,
            number='Q2024-002',
            status='pending',
            total_ttc=2500.00,
            created_at=timezone.now() - timedelta(days=2)
        )
        
        # Create quote item
        QuoteItem.objects.create(
            quote=self.quote,
            description='Nettoyage complet immeuble',
            quantity=1,
            unit_price=2500.00
        )
        
        # Create test task for global planning
        self.task = Task.objects.create(
            title='Nettoyage Immeuble DEF',
            description='Nettoyage complet de l\'immeuble',
            location='789 Boulevard Principal, Cayenne',
            assigned_to=self.worker_user,
            status=Task.STATUS_UPCOMING,
            start_date=timezone.now().date() + timedelta(days=3),
            due_date=timezone.now().date() + timedelta(days=5)
        )
        
        # Create some completed tasks for KPI calculation
        for i in range(3):
            Task.objects.create(
                title=f'Tâche terminée {i+1}',
                description=f'Description tâche {i+1}',
                assigned_to=self.worker_user,
                status='completed',
                completed_at=timezone.now() - timedelta(days=i+1),
                completed_by=self.worker_user
            )
    
    def test_complete_admin_workflow(self):
        """Test the complete admin workflow from login to document validation."""
        
        # Step 1: Admin logs in
        login_successful = self.test_client.login(
            username='admin',
            password='testpass123'
        )
        self.assertTrue(login_successful, "Admin should be able to log in")
        
        # Step 2: Admin accesses their dashboard
        response = self.test_client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Admin', msg_prefix="Should show admin dashboard")
        
        # Step 3: Admin views KPIs
        # Dashboard should show various KPIs
        self.assertContains(response, 'Tâches', msg_prefix="Should show task KPIs")
        self.assertContains(response, 'Revenus', msg_prefix="Should show revenue KPIs")
        
        # Step 4: Admin views global planning
        response = self.test_client.get('/admin-dashboard/planning/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planning Global', msg_prefix="Should show global planning")
        self.assertContains(response, 'Nettoyage Immeuble DEF', msg_prefix="Should show scheduled task")
        self.assertContains(response, 'Pierre Martin', msg_prefix="Should show worker name")
        
        # Step 5: Admin accesses quote validation
        response = self.test_client.get('/gestion/devis/quote/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Q2024-002', msg_prefix="Should show pending quote")
        
        # Step 6: Admin validates the quote
        response = self.test_client.get(f'/gestion/devis/quote/{self.quote.id}/change/')
        self.assertEqual(response.status_code, 200)
        
        # Update quote status to validated
        validation_data = {
            'client': self.devis_client.id,
            'number': 'Q2024-002',
            'status': 'validated',
            'total_ttc': '2500.00',
            'quoteitem_set-TOTAL_FORMS': '1',
            'quoteitem_set-INITIAL_FORMS': '1',
            'quoteitem_set-MIN_NUM_FORMS': '0',
            'quoteitem_set-MAX_NUM_FORMS': '1000',
            'quoteitem_set-0-id': self.quote.quoteitem_set.first().id,
            'quoteitem_set-0-quote': self.quote.id,
            'quoteitem_set-0-description': 'Nettoyage complet immeuble',
            'quoteitem_set-0-quantity': '1',
            'quoteitem_set-0-unit_price': '2500.00',
            '_save': 'Save'
        }
        
        response = self.test_client.post(
            f'/gestion/devis/quote/{self.quote.id}/change/',
            validation_data
        )
        self.assertIn(response.status_code, [200, 302])
        
        # Verify quote was validated
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, 'validated', "Quote should be validated")
        
        # Step 7: Admin checks notifications
        response = self.test_client.get('/admin-dashboard/notifications/')
        self.assertEqual(response.status_code, 200)
        
        # Step 8: Admin accesses messaging
        response = self.test_client.get('/admin-dashboard/messages/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Messages', msg_prefix="Should show messaging interface")
        
        # Step 9: Admin sends a message to client about validated quote
        message_data = {
            'recipient': self.client_user.id,
            'subject': 'Devis validé - Q2024-002',
            'content': '<p>Votre devis Q2024-002 a été validé. Nous procéderons aux travaux prochainement.</p>'
        }
        response = self.test_client.post('/admin-dashboard/messages/compose/', message_data)
        self.assertIn(response.status_code, [200, 302])
        
        # Verify message was created
        message_exists = Message.objects.filter(
            sender=self.admin_user,
            recipient=self.client_user,
            subject__icontains='Devis validé'
        ).exists()
        self.assertTrue(message_exists, "Message should be created")
        
        # Step 10: Admin logs out
        response = self.test_client.post('/accounts/logout/')
        self.assertIn(response.status_code, [200, 302])


@pytest.mark.django_db
class TestCrossPortalIntegration(BaseWorkflowTest):
    """Test integration between different portals and cross-portal functionality."""
    
    def setUp(self):
        super().setUp()
        
        # Create test client (devis.Client)
        self.devis_client = Client.objects.create(
            full_name='Jean Dupont',
            email='client1@test.com',
            phone='0594123456',
            address_line='123 Rue de la Paix',
            city='Cayenne',
            zip_code='97300'
        )
        
        # Create a complete workflow scenario
        self.quote = Quote.objects.create(
            client=self.devis_client,
            number='Q2024-003',
            status='validated',
            total_ttc=3000.00
        )
        
        self.task = Task.objects.create(
            title='Nettoyage suite validation devis',
            description='Nettoyage suite à la validation du devis Q2024-003',
            assigned_to=self.worker_user,
            status=Task.STATUS_UPCOMING,
            start_date=timezone.now().date() + timedelta(days=1),
            due_date=timezone.now().date() + timedelta(days=2)
        )
    
    def test_cross_portal_message_flow(self):
        """Test message flow between different portal users."""
        
        # Client sends message to admin
        self.test_client.login(username='client1', password='testpass123')
        
        message_data = {
            'recipient': self.admin_user.id,
            'subject': 'Question sur planning',
            'content': '<p>Quand aura lieu l\'intervention ?</p>'
        }
        response = self.test_client.post('/client/messages/compose/', message_data)
        self.assertIn(response.status_code, [200, 302])
        
        # Verify message thread was created
        thread = MessageThread.objects.filter(
            participants=self.client_user
        ).first()
        self.assertIsNotNone(thread, "Message thread should be created")
        
        # Admin responds to client
        self.test_client.login(username='admin', password='testpass123')
        
        response_data = {
            'recipient': self.client_user.id,
            'subject': 'Re: Question sur planning',
            'content': '<p>L\'intervention aura lieu demain matin.</p>',
            'thread': thread.id if thread else ''
        }
        response = self.test_client.post('/admin-dashboard/messages/compose/', response_data)
        self.assertIn(response.status_code, [200, 302])
        
        # Verify both users can see the conversation
        self.test_client.login(username='client1', password='testpass123')
        response = self.test_client.get('/client/messages/')
        self.assertEqual(response.status_code, 200)
        
        self.test_client.login(username='admin', password='testpass123')
        response = self.test_client.get('/admin-dashboard/messages/')
        self.assertEqual(response.status_code, 200)
    
    def test_notification_system_integration(self):
        """Test notification system across all portals."""
        
        # Create notifications for different users
        UINotification.objects.create(
            user=self.client_user,
            title='Devis validé',
            message='Votre devis Q2024-003 a été validé',
            notification_type='quote_validated'
        )
        
        UINotification.objects.create(
            user=self.worker_user,
            title='Nouvelle tâche assignée',
            message='Une nouvelle tâche vous a été assignée',
            notification_type='task_assigned'
        )
        
        UINotification.objects.create(
            user=self.admin_user,
            title='Tâche terminée',
            message='Une tâche a été terminée par Pierre Martin',
            notification_type='task_completed'
        )
        
        # Test client can see their notifications
        self.test_client.login(username='client1', password='testpass123')
        response = self.test_client.get('/client/')
        self.assertEqual(response.status_code, 200)
        
        # Test worker can see their notifications
        self.test_client.login(username='worker1', password='testpass123')
        response = self.test_client.get('/worker/')
        self.assertEqual(response.status_code, 200)
        
        # Test admin can see their notifications
        self.test_client.login(username='admin', password='testpass123')
        response = self.test_client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
    
    def test_session_tracking_integration(self):
        """Test session tracking across all portals."""
        
        # Test client session tracking
        self.test_client.login(username='client1', password='testpass123')
        response = self.test_client.get('/client/')
        self.assertEqual(response.status_code, 200)
        
        # Verify session was created
        client_session = PortalSession.objects.filter(
            user=self.client_user,
            portal_type='client'
        ).first()
        self.assertIsNotNone(client_session, "Client session should be tracked")
        
        # Test worker session tracking
        self.test_client.login(username='worker1', password='testpass123')
        response = self.test_client.get('/worker/')
        self.assertEqual(response.status_code, 200)
        
        # Verify session was created
        worker_session = PortalSession.objects.filter(
            user=self.worker_user,
            portal_type='worker'
        ).first()
        self.assertIsNotNone(worker_session, "Worker session should be tracked")
        
        # Test admin business session tracking (/admin-dashboard/)
        admin_business_user = User.objects.create_user(
            username='admin_business',
            email='admin_business@test.com',
            password='testpass123',
            is_staff=True
        )
        admin_business_user.profile.role = Profile.ROLE_ADMIN_BUSINESS
        admin_business_user.profile.save()

        self.test_client.login(username='admin_business', password='testpass123')
        response = self.test_client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
        
        # Verify session was created
        admin_session = PortalSession.objects.filter(
            user=admin_business_user,
            portal_type='admin'
        ).first()
        self.assertIsNotNone(admin_session, "Admin session should be tracked")


@pytest.mark.django_db
class TestWorkflowErrorHandling(BaseWorkflowTest):
    """Test error handling and edge cases in workflows."""
    
    def test_unauthorized_portal_access(self):
        """Test that users cannot access unauthorized portals."""
        
        # Client tries to access worker portal
        self.test_client.login(username='client1', password='testpass123')
        response = self.test_client.get('/worker/')
        # Should redirect or show access denied
        self.assertIn(response.status_code, [302, 403])
        
        # Worker tries to access admin portal
        self.test_client.login(username='worker1', password='testpass123')
        response = self.test_client.get('/admin-dashboard/')
        # Should redirect or show access denied
        self.assertIn(response.status_code, [302, 403])
        
        # Client tries to access admin portal
        self.test_client.login(username='client1', password='testpass123')
        response = self.test_client.get('/admin-dashboard/')
        # Should redirect or show access denied
        self.assertIn(response.status_code, [302, 403])
    
    def test_invalid_document_access(self):
        """Test that users cannot access documents they don't own."""
        
        # Create quote for different client
        other_client_user = User.objects.create_user(
            username='other_client',
            email='other@test.com',
            password='testpass123'
        )
        other_profile, _ = Profile.objects.get_or_create(
            user=other_client_user,
            defaults={'role': 'client'}
        )
        other_client_user.groups.add(self.clients_group)
        
        # Create devis.Client for the other user
        other_devis_client = Client.objects.create(
            full_name='Marie Martin',
            email='other@test.com',
            phone='0594654321',
            address_line='456 Avenue des Palmiers',
            city='Matoury',
            zip_code='97351'
        )
        
        other_quote = Quote.objects.create(
            client=other_devis_client,
            number='Q2024-999',
            status='validated',
            total_ttc=1000.00
        )
        
        # Client tries to access other client's quote
        self.test_client.login(username='client1', password='testpass123')
        response = self.test_client.get(f'/client/quotes/{other_quote.id}/')
        # Should show 404 or access denied
        self.assertIn(response.status_code, [404, 403])
    
    def test_workflow_with_missing_data(self):
        """Test workflows handle missing or incomplete data gracefully."""
        
        # Test client portal with no documents
        self.test_client.login(username='client1', password='testpass123')
        response = self.test_client.get('/client/quotes/')
        self.assertEqual(response.status_code, 200)
        # Should show empty state message
        
        # Test worker portal with no tasks
        self.test_client.login(username='worker1', password='testpass123')
        response = self.test_client.get('/worker/')
        self.assertEqual(response.status_code, 200)
        # Should show empty state message
        
        # Test admin portal with no data
        self.test_client.login(username='admin', password='testpass123')
        response = self.test_client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
        # Should handle zero values gracefully