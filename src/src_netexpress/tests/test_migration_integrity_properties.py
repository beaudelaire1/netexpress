"""
Property-based tests for data migration integrity.

**Feature: netexpress-v2-transformation, Property 11: Data migration integrity**
**Validates: Requirements 10.1, 10.4, 10.5**

These tests verify that the migration process preserves all existing data
and relationships without loss or corruption.
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth.models import User, Group
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta

from accounts.models import Profile
from accounts.management.commands.migrate_users_to_roles import Command as MigrateCommand
from accounts.management.commands.preserve_data_relationships import Command as PreserveCommand


class TestMigrationIntegrityProperties(TestCase):
    """Property-based tests for migration integrity."""

    def setUp(self):
        """Set up test data."""
        # Create groups
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')

    @given(
        user_count=st.integers(min_value=1, max_value=10),
        has_existing_profiles=st.booleans(),
    )
    @settings(max_examples=50, deadline=None)
    def test_user_migration_preserves_all_users(self, user_count, has_existing_profiles):
        """
        Property 11: Data migration integrity - User migration
        
        For any set of existing users, migrating to the role system should preserve
        all user accounts and their basic information (username, email, etc.).
        **Validates: Requirements 10.1, 10.4, 10.5**
        """
        # Create test users
        users_before = []
        for i in range(user_count):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                first_name=f'Test{i}',
                last_name='User'
            )
            
            # Optionally modify existing profiles (they're auto-created by signal)
            if has_existing_profiles and i % 2 == 0:
                user.profile.role = Profile.ROLE_CLIENT
                user.profile.save()
            
            users_before.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            })
        
        # Run migration
        command = MigrateCommand()
        command.handle(dry_run=False, force=True)
        
        # Verify all users still exist with same data
        users_after = User.objects.all()
        self.assertEqual(len(users_after), user_count)
        
        for user_data in users_before:
            user = User.objects.get(id=user_data['id'])
            self.assertEqual(user.username, user_data['username'])
            self.assertEqual(user.email, user_data['email'])
            self.assertEqual(user.first_name, user_data['first_name'])
            self.assertEqual(user.last_name, user_data['last_name'])
            self.assertEqual(user.is_staff, user_data['is_staff'])
            self.assertEqual(user.is_superuser, user_data['is_superuser'])
            
            # Verify user now has a profile
            self.assertTrue(hasattr(user, 'profile'))
            self.assertIsNotNone(user.profile)
            self.assertIn(user.profile.role, [Profile.ROLE_CLIENT, Profile.ROLE_WORKER])

    @given(
        client_count=st.integers(min_value=1, max_value=5),
        quote_count=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=30, deadline=None)
    def test_client_data_relationships_preserved(self, client_count, quote_count):
        """
        Property 11: Data migration integrity - Client relationships
        
        For any existing client data with quotes, the migration should preserve
        all client records and their relationships to quotes and invoices.
        **Validates: Requirements 10.1, 10.4, 10.5**
        """
        try:
            from devis.models import Client, Quote, QuoteItem
            from services.models import Service
        except ImportError:
            pytest.skip("Business models not available")
        
        # Create test service
        service = Service.objects.create(
            title='Test Service',
            description='Test service description',
            price=Decimal('100.00')
        )
        
        # Create test clients and quotes
        clients_before = []
        quotes_before = []
        
        for i in range(client_count):
            client = Client.objects.create(
                full_name=f'Test Client {i}',
                email=f'client{i}@example.com',
                phone=f'012345678{i}',
                address_line=f'{i} Test Street',
                city='Test City',
                zip_code=f'1234{i}'
            )
            clients_before.append({
                'id': client.id,
                'full_name': client.full_name,
                'email': client.email,
                'phone': client.phone,
            })
            
            # Create quotes for this client
            for j in range(quote_count):
                quote = Quote.objects.create(
                    client=client,
                    service=service,
                    message=f'Test quote {j} for client {i}',
                    status=Quote.QuoteStatus.DRAFT,
                    issue_date=date.today(),
                )
                
                # Add quote item
                QuoteItem.objects.create(
                    quote=quote,
                    service=service,
                    description=service.title,
                    quantity=Decimal('1.00'),
                    unit_price=service.price,
                    tax_rate=Decimal('20.00'),
                )
                
                quotes_before.append({
                    'id': quote.id,
                    'client_id': client.id,
                    'message': quote.message,
                    'status': quote.status,
                })
        
        # Run relationship preservation
        command = PreserveCommand()
        command.handle(verify_only=False, fix_orphaned=True)
        
        # Verify all clients still exist
        self.assertEqual(Client.objects.count(), client_count)
        for client_data in clients_before:
            client = Client.objects.get(id=client_data['id'])
            self.assertEqual(client.full_name, client_data['full_name'])
            self.assertEqual(client.email, client_data['email'])
            self.assertEqual(client.phone, client_data['phone'])
        
        # Verify all quotes still exist with correct relationships
        self.assertEqual(Quote.objects.count(), client_count * quote_count)
        for quote_data in quotes_before:
            quote = Quote.objects.get(id=quote_data['id'])
            self.assertEqual(quote.client.id, quote_data['client_id'])
            self.assertEqual(quote.message, quote_data['message'])
            self.assertEqual(quote.status, quote_data['status'])
            
            # Verify quote items are preserved
            self.assertTrue(quote.quote_items.exists())

    @given(
        task_count=st.integers(min_value=1, max_value=5),
        worker_count=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=30, deadline=None)
    def test_task_assignments_preserved(self, task_count, worker_count):
        """
        Property 11: Data migration integrity - Task assignments
        
        For any existing task assignments, the migration should preserve
        all task data and worker assignments.
        **Validates: Requirements 10.1, 10.4, 10.5**
        """
        try:
            from tasks.models import Task
        except ImportError:
            pytest.skip("Task model not available")
        
        # Create worker users
        workers = []
        for i in range(worker_count):
            user = User.objects.create_user(
                username=f'worker{i}',
                email=f'worker{i}@example.com'
            )
            user.groups.add(self.workers_group)
            # Profile is auto-created by signal, just update role
            user.profile.role = Profile.ROLE_WORKER
            user.profile.save()
            workers.append(user)
        
        # Create tasks with assignments
        tasks_before = []
        for i in range(task_count):
            assigned_worker = workers[i % len(workers)] if workers else None
            
            task = Task.objects.create(
                title=f'Test Task {i}',
                description=f'Description for task {i}',
                location=f'Location {i}',
                team='Test Team',
                start_date=date.today(),
                due_date=date.today() + timedelta(days=7),
                assigned_to=assigned_worker,
            )
            
            tasks_before.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'assigned_to_id': assigned_worker.id if assigned_worker else None,
            })
        
        # Run relationship preservation
        command = PreserveCommand()
        command.handle(verify_only=False, fix_orphaned=True)
        
        # Verify all tasks still exist with correct assignments
        self.assertEqual(Task.objects.count(), task_count)
        for task_data in tasks_before:
            task = Task.objects.get(id=task_data['id'])
            self.assertEqual(task.title, task_data['title'])
            self.assertEqual(task.description, task_data['description'])
            
            if task_data['assigned_to_id']:
                self.assertIsNotNone(task.assigned_to)
                self.assertEqual(task.assigned_to.id, task_data['assigned_to_id'])
                # Verify worker is in correct group
                self.assertTrue(task.assigned_to.groups.filter(name='Workers').exists())

    @given(
        user_data=st.lists(
            st.tuples(
                st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
                st.emails(),
                st.booleans(),  # is_staff
                st.booleans(),  # has_tasks
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_role_assignment_consistency(self, user_data):
        """
        Property 11: Data migration integrity - Role assignment consistency
        
        For any set of users with different characteristics, the migration should
        assign roles consistently based on the same logic every time.
        **Validates: Requirements 10.1, 10.4, 10.5**
        """
        try:
            from tasks.models import Task
        except ImportError:
            pytest.skip("Task model not available")
        
        # Create users with different characteristics
        users_created = []
        expected_roles = []
        
        for username, email, is_staff, has_tasks in user_data:
            # Ensure unique username and email
            username = f"test_{username}_{len(users_created)}"
            email = f"test_{len(users_created)}_{email}"
            
            user = User.objects.create_user(
                username=username,
                email=email,
                is_staff=is_staff
            )
            
            # Create tasks if needed
            if has_tasks:
                Task.objects.create(
                    title=f'Task for {username}',
                    start_date=date.today(),
                    due_date=date.today() + timedelta(days=1),
                    assigned_to=user
                )
                expected_roles.append(Profile.ROLE_WORKER)
            else:
                expected_roles.append(Profile.ROLE_CLIENT)
            
            users_created.append(user)
        
        # Run migration multiple times
        command = MigrateCommand()
        
        # First migration
        command.handle(dry_run=False, force=True)
        roles_first = [user.profile.role for user in users_created]
        
        # Second migration (should be consistent)
        command.handle(dry_run=False, force=True)
        roles_second = [user.profile.role for user in users_created]
        
        # Verify consistency
        self.assertEqual(roles_first, roles_second)
        
        # Verify roles match expectations (workers for users with tasks)
        for i, (user, expected_role) in enumerate(zip(users_created, expected_roles)):
            if expected_role == Profile.ROLE_WORKER:
                self.assertEqual(user.profile.role, Profile.ROLE_WORKER)
                self.assertTrue(user.groups.filter(name='Workers').exists())
            else:
                # Default to client for non-workers
                self.assertEqual(user.profile.role, Profile.ROLE_CLIENT)

    def test_migration_preserves_superuser_status(self):
        """
        Property 11: Data migration integrity - Superuser preservation
        
        Migration should never modify superuser or staff status of existing users.
        **Validates: Requirements 10.1, 10.4, 10.5**
        """
        # Create superuser
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass'
        )
        
        # Create staff user
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            is_staff=True
        )
        
        # Run migration
        command = MigrateCommand()
        command.handle(dry_run=False, force=True)
        
        # Verify superuser status preserved
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
        
        # Verify staff status preserved
        staff_user.refresh_from_db()
        self.assertTrue(staff_user.is_staff)
        self.assertFalse(staff_user.is_superuser)