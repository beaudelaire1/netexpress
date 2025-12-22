from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from accounts.models import Profile


class Command(BaseCommand):
    help = 'Migrate existing users to the new role-based system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if some users already have roles',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Ensure groups exist
        clients_group, _ = Group.objects.get_or_create(name='Clients')
        workers_group, _ = Group.objects.get_or_create(name='Workers')
        
        # Get all users
        users = User.objects.all()
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        with transaction.atomic():
            for user in users:
                try:
                    # Get or create profile
                    profile, created = Profile.objects.get_or_create(user=user)
                    
                    # Skip if user already has a role and not forcing
                    if profile.role and not force:
                        self.stdout.write(f'Skipping {user.username} - already has role: {profile.role}')
                        skipped_count += 1
                        continue
                    
                    # Determine role based on existing characteristics
                    new_role = self._determine_user_role(user)
                    
                    if not dry_run:
                        # Update profile role
                        profile.role = new_role
                        profile.save()
                        
                        # Add user to appropriate group
                        if new_role == Profile.ROLE_CLIENT:
                            user.groups.add(clients_group)
                            user.groups.remove(workers_group)
                        elif new_role == Profile.ROLE_WORKER:
                            user.groups.add(workers_group)
                            user.groups.remove(clients_group)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'{"Would migrate" if dry_run else "Migrated"} {user.username} to role: {new_role}'
                        )
                    )
                    migrated_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error migrating {user.username}: {e}')
                    )
                    error_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Migration Summary:')
        self.stdout.write(f'  Migrated: {migrated_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Errors: {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nThis was a dry run. Use --force to apply changes.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nMigration completed successfully!')
            )

    def _determine_user_role(self, user):
        """
        Determine the appropriate role for a user based on existing data.
        
        Logic:
        1. If user is staff/superuser -> keep as admin (no profile role change needed)
        2. If user has assigned tasks -> worker
        3. If user is linked to quotes/invoices via Client model -> client
        4. Default -> client
        """
        # Staff/superuser users don't get profile roles - they use Django admin
        if user.is_staff or user.is_superuser:
            return Profile.ROLE_CLIENT  # Default, but they won't use portals
        
        # Check if user has assigned tasks (worker indicator)
        if hasattr(user, 'assigned_tasks') and user.assigned_tasks.exists():
            return Profile.ROLE_WORKER
        
        # Check if user is linked to business data as a client
        # This is more complex as we need to check if there's a Client record
        # with matching email that has quotes/invoices
        try:
            from devis.models import Client
            client_records = Client.objects.filter(email=user.email)
            if client_records.exists():
                # Check if any of these client records have quotes or invoices
                for client in client_records:
                    if client.quotes.exists():
                        return Profile.ROLE_CLIENT
        except Exception:
            pass  # If models don't exist yet, continue
        
        # Default to client role
        return Profile.ROLE_CLIENT