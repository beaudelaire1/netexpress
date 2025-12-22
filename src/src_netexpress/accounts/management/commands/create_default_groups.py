from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Create default groups (Clients and Workers) with appropriate permissions'

    def handle(self, *args, **options):
        # Create Clients group
        clients_group, created = Group.objects.get_or_create(name='Clients')
        if created:
            self.stdout.write(
                self.style.SUCCESS('Successfully created "Clients" group')
            )
        else:
            self.stdout.write('Group "Clients" already exists')

        # Create Workers group
        workers_group, created = Group.objects.get_or_create(name='Workers')
        if created:
            self.stdout.write(
                self.style.SUCCESS('Successfully created "Workers" group')
            )
        else:
            self.stdout.write('Group "Workers" already exists')

        # Set up permissions for Clients group
        # Clients should be able to view their own documents and send messages
        client_permissions = [
            'view_quote',
            'view_invoice',
            'add_message',
            'view_message',
        ]
        
        # Get content types for the models we need
        try:
            from devis.models import Quote
            from factures.models import Invoice
            
            quote_ct = ContentType.objects.get_for_model(Quote)
            invoice_ct = ContentType.objects.get_for_model(Invoice)
            
            # Add quote and invoice view permissions to Clients group
            quote_view_perm = Permission.objects.get(
                codename='view_quote',
                content_type=quote_ct
            )
            invoice_view_perm = Permission.objects.get(
                codename='view_invoice',
                content_type=invoice_ct
            )
            
            clients_group.permissions.add(quote_view_perm, invoice_view_perm)
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not set up all client permissions: {e}')
            )

        # Set up permissions for Workers group
        # Workers should be able to view and update their assigned tasks
        try:
            from tasks.models import Task
            
            task_ct = ContentType.objects.get_for_model(Task)
            
            # Add task permissions to Workers group
            task_view_perm = Permission.objects.get(
                codename='view_task',
                content_type=task_ct
            )
            task_change_perm = Permission.objects.get(
                codename='change_task',
                content_type=task_ct
            )
            
            workers_group.permissions.add(task_view_perm, task_change_perm)
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not set up all worker permissions: {e}')
            )

        self.stdout.write(
            self.style.SUCCESS('Default groups setup completed')
        )