from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    help = 'Preserve and verify existing data relationships during migration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='Only verify relationships without making changes',
        )
        parser.add_argument(
            '--fix-orphaned',
            action='store_true',
            help='Attempt to fix orphaned records',
        )

    def handle(self, *args, **options):
        verify_only = options['verify_only']
        fix_orphaned = options['fix_orphaned']
        
        self.stdout.write('Checking data relationship integrity...\n')
        
        # Check and preserve Client -> User relationships
        self._check_client_user_relationships(verify_only, fix_orphaned)
        
        # Check Task -> User assignments
        self._check_task_user_assignments(verify_only, fix_orphaned)
        
        # Check Quote -> Client relationships
        self._check_quote_client_relationships(verify_only, fix_orphaned)
        
        # Check Invoice -> Quote relationships
        self._check_invoice_quote_relationships(verify_only, fix_orphaned)
        
        self.stdout.write(
            self.style.SUCCESS('\nData relationship verification completed!')
        )

    def _check_client_user_relationships(self, verify_only, fix_orphaned):
        """Check and preserve Client model relationships with User accounts."""
        self.stdout.write('Checking Client -> User relationships...')
        
        try:
            from devis.models import Client
            
            clients_with_users = 0
            clients_without_users = 0
            orphaned_clients = []
            
            for client in Client.objects.all():
                try:
                    # Try to find a user with matching email
                    user = User.objects.get(email=client.email)
                    clients_with_users += 1
                    
                    # Verify the user has a profile
                    if not hasattr(user, 'profile'):
                        self.stdout.write(
                            self.style.WARNING(f'User {user.username} missing profile')
                        )
                        if not verify_only:
                            from accounts.models import Profile
                            Profile.objects.create(user=user, role=Profile.ROLE_CLIENT)
                            self.stdout.write(f'Created profile for {user.username}')
                    
                except User.DoesNotExist:
                    clients_without_users += 1
                    orphaned_clients.append(client)
                    
                    if fix_orphaned and not verify_only:
                        # Create user account for orphaned client
                        username = self._generate_username_from_email(client.email)
                        user = User.objects.create_user(
                            username=username,
                            email=client.email,
                            first_name=client.full_name.split()[0] if client.full_name else '',
                            last_name=' '.join(client.full_name.split()[1:]) if len(client.full_name.split()) > 1 else ''
                        )
                        self.stdout.write(f'Created user account for client: {client.email}')
            
            self.stdout.write(f'  Clients with user accounts: {clients_with_users}')
            self.stdout.write(f'  Clients without user accounts: {clients_without_users}')
            
            if orphaned_clients and not fix_orphaned:
                self.stdout.write(
                    self.style.WARNING(
                        f'  Use --fix-orphaned to create user accounts for orphaned clients'
                    )
                )
                
        except ImportError:
            self.stdout.write(
                self.style.WARNING('Client model not available - skipping client checks')
            )

    def _check_task_user_assignments(self, verify_only, fix_orphaned):
        """Check Task model user assignments."""
        self.stdout.write('Checking Task -> User assignments...')
        
        try:
            from tasks.models import Task
            
            tasks_with_assignments = Task.objects.filter(assigned_to__isnull=False).count()
            tasks_without_assignments = Task.objects.filter(assigned_to__isnull=True).count()
            
            self.stdout.write(f'  Tasks with worker assignments: {tasks_with_assignments}')
            self.stdout.write(f'  Tasks without assignments: {tasks_without_assignments}')
            
            # Check for invalid assignments (users not in Workers group)
            invalid_assignments = 0
            for task in Task.objects.filter(assigned_to__isnull=False):
                if not task.assigned_to.groups.filter(name='Workers').exists():
                    invalid_assignments += 1
                    if fix_orphaned and not verify_only:
                        # Add user to Workers group
                        from django.contrib.auth.models import Group
                        workers_group, _ = Group.objects.get_or_create(name='Workers')
                        task.assigned_to.groups.add(workers_group)
                        
                        # Ensure user has worker profile
                        if hasattr(task.assigned_to, 'profile'):
                            task.assigned_to.profile.role = 'worker'
                            task.assigned_to.profile.save()
                        
                        self.stdout.write(f'Fixed worker assignment for {task.assigned_to.username}')
            
            if invalid_assignments > 0:
                self.stdout.write(f'  Invalid worker assignments: {invalid_assignments}')
                
        except ImportError:
            self.stdout.write(
                self.style.WARNING('Task model not available - skipping task checks')
            )

    def _check_quote_client_relationships(self, verify_only, fix_orphaned):
        """Check Quote -> Client relationships."""
        self.stdout.write('Checking Quote -> Client relationships...')
        
        try:
            from devis.models import Quote, Client
            
            total_quotes = Quote.objects.count()
            quotes_with_clients = Quote.objects.filter(client__isnull=False).count()
            orphaned_quotes = total_quotes - quotes_with_clients
            
            self.stdout.write(f'  Total quotes: {total_quotes}')
            self.stdout.write(f'  Quotes with clients: {quotes_with_clients}')
            self.stdout.write(f'  Orphaned quotes: {orphaned_quotes}')
            
            if orphaned_quotes > 0 and not fix_orphaned:
                self.stdout.write(
                    self.style.WARNING('  Some quotes are missing client relationships')
                )
                
        except ImportError:
            self.stdout.write(
                self.style.WARNING('Quote/Client models not available - skipping quote checks')
            )

    def _check_invoice_quote_relationships(self, verify_only, fix_orphaned):
        """Check Invoice -> Quote relationships."""
        self.stdout.write('Checking Invoice -> Quote relationships...')
        
        try:
            from factures.models import Invoice
            
            total_invoices = Invoice.objects.count()
            invoices_with_quotes = Invoice.objects.filter(quote__isnull=False).count()
            standalone_invoices = total_invoices - invoices_with_quotes
            
            self.stdout.write(f'  Total invoices: {total_invoices}')
            self.stdout.write(f'  Invoices linked to quotes: {invoices_with_quotes}')
            self.stdout.write(f'  Standalone invoices: {standalone_invoices}')
            
        except ImportError:
            self.stdout.write(
                self.style.WARNING('Invoice model not available - skipping invoice checks')
            )

    def _generate_username_from_email(self, email):
        """Generate a unique username from an email address."""
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        return username