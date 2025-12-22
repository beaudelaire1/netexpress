"""
Unit tests for data migration scripts.

These tests verify the specific functionality of migration commands
and backward compatibility features.
"""

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from unittest.mock import patch, MagicMock

from accounts.models import Profile
from accounts.management.commands.migrate_users_to_roles import Command as MigrateCommand
from accounts.management.commands.preserve_data_relationships import Command as PreserveCommand
from core.management.commands.seed_demo_data import Command as SeedCommand
from core.compatibility import (
    BackwardCompatibilityMiddleware, 
    ensure_profile_exists, 
    get_user_portal_url,
    LegacyViewMixin
)


class TestUserMigrationCommand(TestCase):
    """Unit tests for user migration to role system."""

    def setUp(self):
        """Set up test data."""
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')

    def test_migrate_command_dry_run(self):
        """Test migration command in dry run mode."""
        # Create test user and clear its role to simulate pre-migration state
        user = User.objects.create_user(username='testuser', email='test@example.com')
        user.profile.role = ''  # Clear role to simulate pre-migration
        user.profile.save()
        
        # Run dry run
        out = StringIO()
        command = MigrateCommand()
        command.stdout = out
        command.handle(dry_run=True, force=True)  # Use force to override existing role
        
        output = out.getvalue()
        self.assertIn('DRY RUN MODE', output)
        self.assertIn('Would migrate', output)
        
        # Verify no changes were made (role should still be empty)
        user.refresh_from_db()
        self.assertEqual(user.profile.role, '')  # Should remain unchanged in dry run

    def test_migrate_command_creates_groups(self):
        """Test that migration command creates required groups."""
        # Delete groups if they exist
        Group.objects.filter(name__in=['Clients', 'Workers']).delete()
        
        command = MigrateCommand()
        command.handle(dry_run=False, force=False)
        
        # Verify groups were created
        self.assertTrue(Group.objects.filter(name='Clients').exists())
        self.assertTrue(Group.objects.filter(name='Workers').exists())

    def test_migrate_command_skips_existing_roles(self):
        """Test that migration skips users who already have roles."""
        # Create user with existing role
        user = User.objects.create_user(username='testuser', email='test@example.com')
        user.profile.role = Profile.ROLE_WORKER
        user.profile.save()
        
        out = StringIO()
        command = MigrateCommand()
        command.stdout = out
        command.handle(dry_run=False, force=False)
        
        output = out.getvalue()
        self.assertIn('Skipping testuser', output)
        self.assertIn('already has role', output)

    def test_migrate_command_force_override(self):
        """Test that force flag overrides existing roles."""
        # Create user with existing role
        user = User.objects.create_user(username='testuser', email='test@example.com')
        user.profile.role = Profile.ROLE_WORKER
        user.profile.save()
        
        out = StringIO()
        command = MigrateCommand()
        command.stdout = out
        command.handle(dry_run=False, force=True)
        
        output = out.getvalue()
        self.assertIn('Migrated testuser', output)

    def test_determine_user_role_staff(self):
        """Test role determination for staff users."""
        user = User.objects.create_user(
            username='staff', 
            email='staff@example.com',
            is_staff=True
        )
        
        command = MigrateCommand()
        role = command._determine_user_role(user)
        
        # Staff users get client role (they use admin interface)
        self.assertEqual(role, Profile.ROLE_CLIENT)

    def test_determine_user_role_with_tasks(self):
        """Test role determination for users with assigned tasks."""
        try:
            from tasks.models import Task
            
            user = User.objects.create_user(username='worker', email='worker@example.com')
            
            # Create task assigned to user
            Task.objects.create(
                title='Test Task',
                start_date='2024-01-01',
                due_date='2024-01-02',
                assigned_to=user
            )
            
            command = MigrateCommand()
            role = command._determine_user_role(user)
            
            self.assertEqual(role, Profile.ROLE_WORKER)
            
        except ImportError:
            self.skipTest("Task model not available")

    def test_determine_user_role_default(self):
        """Test default role determination."""
        user = User.objects.create_user(username='regular', email='regular@example.com')
        
        command = MigrateCommand()
        role = command._determine_user_role(user)
        
        self.assertEqual(role, Profile.ROLE_CLIENT)


class TestDataRelationshipPreservation(TestCase):
    """Unit tests for data relationship preservation."""

    def setUp(self):
        """Set up test data."""
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')

    def test_preserve_command_verify_only(self):
        """Test preserve command in verify-only mode."""
        user = User.objects.create_user(username='testuser', email='test@example.com')
        
        out = StringIO()
        command = PreserveCommand()
        command.stdout = out
        command.handle(verify_only=True, fix_orphaned=False)
        
        output = out.getvalue()
        self.assertIn('Checking data relationship integrity', output)

    def test_client_user_relationship_check(self):
        """Test client-user relationship checking."""
        try:
            from devis.models import Client
            
            # Create client without corresponding user
            client = Client.objects.create(
                full_name='Test Client',
                email='client@example.com',
                phone='1234567890'
            )
            
            out = StringIO()
            command = PreserveCommand()
            command.stdout = out
            command.handle(verify_only=True, fix_orphaned=False)
            
            output = out.getvalue()
            self.assertIn('Clients without user accounts: 1', output)
            
        except ImportError:
            self.skipTest("Client model not available")

    def test_fix_orphaned_clients(self):
        """Test fixing orphaned client records."""
        try:
            from devis.models import Client
            
            # Create client without corresponding user
            client = Client.objects.create(
                full_name='Test Client',
                email='orphan@example.com',
                phone='1234567890'
            )
            
            command = PreserveCommand()
            command.handle(verify_only=False, fix_orphaned=True)
            
            # Verify user was created
            self.assertTrue(User.objects.filter(email='orphan@example.com').exists())
            
        except ImportError:
            self.skipTest("Client model not available")

    def test_generate_username_from_email(self):
        """Test username generation from email."""
        command = PreserveCommand()
        
        # Test basic email
        username = command._generate_username_from_email('test@example.com')
        self.assertEqual(username, 'test')
        
        # Test with existing user
        User.objects.create_user(username='test', email='existing@example.com')
        username = command._generate_username_from_email('test@example.com')
        self.assertEqual(username, 'test1')


class TestDemoDataSeeding(TestCase):
    """Unit tests for demo data seeding."""

    def setUp(self):
        """Set up test data."""
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')

    def test_seed_command_users_only(self):
        """Test seeding only users."""
        out = StringIO()
        command = SeedCommand()
        command.stdout = out
        command.handle(clear_existing=False, users_only=True)
        
        output = out.getvalue()
        self.assertIn('Demo data created successfully', output)
        
        # Verify demo users were created
        self.assertTrue(User.objects.filter(username='demo_admin').exists())
        self.assertTrue(User.objects.filter(username='demo_client1').exists())
        self.assertTrue(User.objects.filter(username='demo_worker1').exists())

    def test_seed_command_clear_existing(self):
        """Test clearing existing demo data."""
        # Create some demo data first
        User.objects.create_user(username='demo_test', email='demo@example.com')
        
        out = StringIO()
        command = SeedCommand()
        command.stdout = out
        command.handle(clear_existing=True, users_only=True)
        
        # Verify old demo data was cleared
        self.assertFalse(User.objects.filter(username='demo_test').exists())

    def test_create_demo_users(self):
        """Test demo user creation."""
        command = SeedCommand()
        admin_user, client_users, worker_users = command._create_demo_users()
        
        # Verify admin user
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        
        # Verify client users
        self.assertEqual(len(client_users), 3)
        for user in client_users:
            self.assertTrue(user.groups.filter(name='Clients').exists())
            self.assertEqual(user.profile.role, Profile.ROLE_CLIENT)
        
        # Verify worker users
        self.assertEqual(len(worker_users), 2)
        for user in worker_users:
            self.assertTrue(user.groups.filter(name='Workers').exists())
            self.assertEqual(user.profile.role, Profile.ROLE_WORKER)


class TestBackwardCompatibility(TestCase):
    """Unit tests for backward compatibility features."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )

    def test_ensure_profile_exists_creates_profile(self):
        """Test that ensure_profile_exists creates missing profiles."""
        # Create user without profile (bypass signal)
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com'
        )
        # Delete the auto-created profile
        user.profile.delete()
        
        # Verify profile is deleted
        user.refresh_from_db()
        with self.assertRaises(Profile.DoesNotExist):
            _ = user.profile
        
        # Ensure profile exists
        ensure_profile_exists(user)
        
        # Refresh user to get the new profile
        user.refresh_from_db()
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile)

    def test_ensure_profile_exists_no_duplicate(self):
        """Test that ensure_profile_exists doesn't create duplicates."""
        # Profile should already exist from signal
        profile_count_before = Profile.objects.filter(user=self.user).count()
        ensure_profile_exists(self.user)
        profile_count_after = Profile.objects.filter(user=self.user).count()
        
        self.assertEqual(profile_count_before, profile_count_after)

    def test_get_user_portal_url_client(self):
        """Test portal URL for client user."""
        self.user.profile.role = Profile.ROLE_CLIENT
        self.user.profile.save()
        
        url = get_user_portal_url(self.user)
        self.assertEqual(url, 'core:client_portal_dashboard')

    def test_get_user_portal_url_worker(self):
        """Test portal URL for worker user."""
        self.user.profile.role = Profile.ROLE_WORKER
        self.user.profile.save()
        
        url = get_user_portal_url(self.user)
        self.assertEqual(url, 'tasks:worker_dashboard')

    def test_get_user_portal_url_staff(self):
        """Test portal URL for staff user."""
        self.user.is_staff = True
        self.user.save()
        
        url = get_user_portal_url(self.user)
        self.assertEqual(url, 'core:admin_dashboard')

    def test_get_user_portal_url_anonymous(self):
        """Test portal URL for anonymous user."""
        from django.contrib.auth.models import AnonymousUser
        
        url = get_user_portal_url(AnonymousUser())
        self.assertEqual(url, 'accounts:login')

    def test_backward_compatibility_middleware_init(self):
        """Test middleware initialization."""
        get_response = MagicMock()
        middleware = BackwardCompatibilityMiddleware(get_response)
        
        self.assertEqual(middleware.get_response, get_response)
        self.assertIn('/dashboard/', middleware.legacy_redirects)

    def test_legacy_view_mixin_dispatch(self):
        """Test legacy view mixin dispatch method."""
        from django.http import HttpRequest, HttpResponse
        from django.views.generic import View
        
        class TestView(LegacyViewMixin, View):
            def get(self, request):
                return HttpResponse('OK')
        
        request = HttpRequest()
        request.method = 'GET'
        request.user = self.user
        
        view = TestView()
        # Should not raise any exceptions
        response = view.dispatch(request)
        self.assertIsNotNone(response)

    def test_legacy_view_mixin_context(self):
        """Test legacy view mixin context data."""
        from django.http import HttpRequest
        from django.views.generic import TemplateView
        
        class TestView(LegacyViewMixin, TemplateView):
            template_name = 'test.html'
        
        request = HttpRequest()
        request.user = self.user
        
        view = TestView()
        view.request = request
        context = view.get_context_data()
        
        self.assertTrue(context['is_legacy_view'])
        self.assertIsNotNone(context['portal_url'])


class TestMigrationIntegration(TestCase):
    """Integration tests for migration workflow."""

    def setUp(self):
        """Set up test data."""
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')

    def test_full_migration_workflow(self):
        """Test complete migration workflow."""
        # Create test users
        client_user = User.objects.create_user(
            username='client',
            email='client@example.com'
        )
        worker_user = User.objects.create_user(
            username='worker',
            email='worker@example.com'
        )
        
        # Create task for worker (to influence role assignment)
        try:
            from tasks.models import Task
            Task.objects.create(
                title='Test Task',
                start_date='2024-01-01',
                due_date='2024-01-02',
                assigned_to=worker_user
            )
        except ImportError:
            pass  # Skip if tasks app not available
        
        # Run migration
        migrate_command = MigrateCommand()
        migrate_command.handle(dry_run=False, force=True)
        
        # Run relationship preservation
        preserve_command = PreserveCommand()
        preserve_command.handle(verify_only=False, fix_orphaned=True)
        
        # Verify results
        client_user.refresh_from_db()
        worker_user.refresh_from_db()
        
        # Both should have profiles
        self.assertTrue(hasattr(client_user, 'profile'))
        self.assertTrue(hasattr(worker_user, 'profile'))
        
        # Worker should be in workers group if task exists
        if hasattr(worker_user, 'assigned_tasks') and worker_user.assigned_tasks.exists():
            self.assertTrue(worker_user.groups.filter(name='Workers').exists())

    def test_migration_error_handling(self):
        """Test migration error handling."""
        # Create user with invalid email to trigger error
        user = User.objects.create_user(
            username='invalid',
            email='invalid-email'  # This might cause issues in some scenarios
        )
        
        # Migration should handle errors gracefully
        out = StringIO()
        command = MigrateCommand()
        command.stdout = out
        
        # Should not raise exception
        command.handle(dry_run=False, force=False)
        
        output = out.getvalue()
        self.assertIn('Migration Summary', output)