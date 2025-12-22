from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Create demo data for testing NetExpress v2 portals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing demo data before creating new data',
        )
        parser.add_argument(
            '--users-only',
            action='store_true',
            help='Only create demo users, skip business data',
        )

    def handle(self, *args, **options):
        clear_existing = options['clear_existing']
        users_only = options['users_only']
        
        if clear_existing:
            self.stdout.write('Clearing existing demo data...')
            self._clear_demo_data()
        
        self.stdout.write('Creating demo data for NetExpress v2...')
        
        with transaction.atomic():
            # Create groups first
            self._create_groups()
            
            # Create demo users
            admin_user, client_users, worker_users = self._create_demo_users()
            
            if not users_only:
                # Create business data
                clients = self._create_demo_clients(client_users)
                services = self._create_demo_services()
                quotes = self._create_demo_quotes(clients, services)
                invoices = self._create_demo_invoices(quotes)
                tasks = self._create_demo_tasks(worker_users, clients)
                messages = self._create_demo_messages(admin_user, client_users, worker_users)
        
        self.stdout.write(
            self.style.SUCCESS('Demo data created successfully!')
        )
        
        # Print summary
        self._print_summary(admin_user, client_users, worker_users)

    def _clear_demo_data(self):
        """Clear existing demo data."""
        # Clear in reverse dependency order
        try:
            from messaging.models import Message
            Message.objects.filter(sender__username__startswith='demo_').delete()
        except ImportError:
            pass
        
        try:
            from tasks.models import Task
            Task.objects.filter(title__startswith='Demo').delete()
        except ImportError:
            pass
        
        try:
            from factures.models import Invoice
            Invoice.objects.filter(number__startswith='DEMO-').delete()
        except ImportError:
            pass
        
        try:
            from devis.models import Quote, Client
            Quote.objects.filter(number__startswith='DEMO-').delete()
            Client.objects.filter(full_name__startswith='Demo').delete()
        except ImportError:
            pass
        
        # Clear demo users
        User.objects.filter(username__startswith='demo_').delete()

    def _create_groups(self):
        """Create required groups."""
        clients_group, created = Group.objects.get_or_create(name='Clients')
        workers_group, created = Group.objects.get_or_create(name='Workers')
        
        self.stdout.write('Groups created/verified')

    def _create_demo_users(self):
        """Create demo users for testing."""
        # Admin user
        admin_user, created = User.objects.get_or_create(
            username='demo_admin',
            defaults={
                'email': 'admin@netexpress-demo.com',
                'first_name': 'Admin',
                'last_name': 'NetExpress',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('demo123')
            admin_user.save()
        
        # Client users
        client_data = [
            ('demo_client1', 'client1@netexpress-demo.com', 'Marie', 'Dupont'),
            ('demo_client2', 'client2@netexpress-demo.com', 'Pierre', 'Martin'),
            ('demo_client3', 'client3@netexpress-demo.com', 'Sophie', 'Bernard'),
        ]
        
        client_users = []
        clients_group = Group.objects.get(name='Clients')
        
        for username, email, first_name, last_name in client_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            if created:
                user.set_password('demo123')
                user.save()
                user.groups.add(clients_group)
                
                # Profile is auto-created by signal, just update role
                user.profile.role = Profile.ROLE_CLIENT
                user.profile.save()
            
            client_users.append(user)
        
        # Worker users
        worker_data = [
            ('demo_worker1', 'worker1@netexpress-demo.com', 'Jean', 'Leroy'),
            ('demo_worker2', 'worker2@netexpress-demo.com', 'Paul', 'Moreau'),
        ]
        
        worker_users = []
        workers_group = Group.objects.get(name='Workers')
        
        for username, email, first_name, last_name in worker_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            if created:
                user.set_password('demo123')
                user.save()
                user.groups.add(workers_group)
                
                # Profile is auto-created by signal, just update role
                user.profile.role = Profile.ROLE_WORKER
                user.profile.save()
            
            worker_users.append(user)
        
        self.stdout.write(f'Created {len(client_users)} client users and {len(worker_users)} worker users')
        return admin_user, client_users, worker_users

    def _create_demo_clients(self, client_users):
        """Create demo client records."""
        try:
            from devis.models import Client
        except ImportError:
            self.stdout.write('Devis app not available - skipping clients')
            return []
        
        clients = []
        client_data = [
            ('Demo Client Marie Dupont', 'client1@netexpress-demo.com', '0123456789', '123 Rue de la Paix', 'Paris', '75001'),
            ('Demo Client Pierre Martin', 'client2@netexpress-demo.com', '0123456790', '456 Avenue des Champs', 'Lyon', '69001'),
            ('Demo Client Sophie Bernard', 'client3@netexpress-demo.com', '0123456791', '789 Boulevard Saint-Germain', 'Marseille', '13001'),
        ]
        
        for full_name, email, phone, address, city, zip_code in client_data:
            client, created = Client.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': full_name,
                    'phone': phone,
                    'address_line': address,
                    'city': city,
                    'zip_code': zip_code,
                }
            )
            clients.append(client)
        
        self.stdout.write(f'Created {len(clients)} demo clients')
        return clients

    def _create_demo_services(self):
        """Create demo services."""
        try:
            from services.models import Service
        except ImportError:
            self.stdout.write('Services app not available - skipping services')
            return []
        
        services = []
        service_data = [
            ('Nettoyage de vitres', 'Nettoyage professionnel des vitres', Decimal('25.00')),
            ('Entretien espaces verts', 'Tonte et entretien des espaces verts', Decimal('40.00')),
            ('Peinture intérieure', 'Peinture et rénovation intérieure', Decimal('35.00')),
            ('Bricolage général', 'Petits travaux de bricolage', Decimal('30.00')),
        ]
        
        for title, description, price in service_data:
            service, created = Service.objects.get_or_create(
                title=title,
                defaults={
                    'description': description,
                    'price': price,
                }
            )
            services.append(service)
        
        self.stdout.write(f'Created {len(services)} demo services')
        return services

    def _create_demo_quotes(self, clients, services):
        """Create demo quotes."""
        try:
            from devis.models import Quote, QuoteItem
        except ImportError:
            self.stdout.write('Devis app not available - skipping quotes')
            return []
        
        if not clients or not services:
            return []
        
        quotes = []
        statuses = [Quote.QuoteStatus.DRAFT, Quote.QuoteStatus.SENT, Quote.QuoteStatus.ACCEPTED]
        
        for i, client in enumerate(clients):
            quote = Quote.objects.create(
                number=f'DEMO-2024-{i+1:03d}',
                client=client,
                service=random.choice(services),
                message=f'Devis de démonstration pour {client.full_name}',
                status=random.choice(statuses),
                issue_date=date.today() - timedelta(days=random.randint(1, 30)),
                valid_until=date.today() + timedelta(days=30),
            )
            
            # Add quote items
            for j in range(random.randint(1, 3)):
                service = random.choice(services)
                QuoteItem.objects.create(
                    quote=quote,
                    service=service,
                    description=service.title,
                    quantity=Decimal(str(random.randint(1, 5))),
                    unit_price=service.price,
                    tax_rate=Decimal('20.00'),
                )
            
            quote.compute_totals()
            quotes.append(quote)
        
        self.stdout.write(f'Created {len(quotes)} demo quotes')
        return quotes

    def _create_demo_invoices(self, quotes):
        """Create demo invoices."""
        try:
            from factures.models import Invoice, InvoiceItem
        except ImportError:
            self.stdout.write('Factures app not available - skipping invoices')
            return []
        
        if not quotes:
            return []
        
        invoices = []
        
        # Create invoices for accepted quotes
        accepted_quotes = [q for q in quotes if q.status == 'accepted']
        
        for i, quote in enumerate(accepted_quotes[:2]):  # Create 2 demo invoices
            invoice = Invoice.objects.create(
                number=f'DEMO-FAC-2024-{i+1:03d}',
                quote=quote,
                issue_date=date.today() - timedelta(days=random.randint(1, 15)),
                status=random.choice(['draft', 'sent', 'paid']),
            )
            
            # Copy quote items to invoice
            for quote_item in quote.quote_items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=quote_item.description,
                    quantity=int(quote_item.quantity),
                    unit_price=quote_item.unit_price,
                    tax_rate=quote_item.tax_rate,
                )
            
            invoice.compute_totals()
            invoices.append(invoice)
        
        self.stdout.write(f'Created {len(invoices)} demo invoices')
        return invoices

    def _create_demo_tasks(self, worker_users, clients):
        """Create demo tasks."""
        try:
            from tasks.models import Task
        except ImportError:
            self.stdout.write('Tasks app not available - skipping tasks')
            return []
        
        if not worker_users:
            return []
        
        tasks = []
        task_data = [
            ('Demo: Nettoyage vitres bureau', 'Nettoyage des vitres du bureau principal', '123 Rue de la Paix, Paris'),
            ('Demo: Entretien jardin', 'Tonte et entretien du jardin', '456 Avenue des Champs, Lyon'),
            ('Demo: Peinture salon', 'Peinture du salon et couloir', '789 Boulevard Saint-Germain, Marseille'),
            ('Demo: Réparation clôture', 'Réparation de la clôture du jardin', '321 Rue de Rivoli, Paris'),
        ]
        
        statuses = ['upcoming', 'in_progress', 'completed']
        
        for i, (title, description, location) in enumerate(task_data):
            start_date = date.today() + timedelta(days=random.randint(-5, 10))
            due_date = start_date + timedelta(days=random.randint(1, 7))
            
            task = Task.objects.create(
                title=title,
                description=description,
                location=location,
                team='Équipe Demo',
                start_date=start_date,
                due_date=due_date,
                status=random.choice(statuses),
                assigned_to=random.choice(worker_users),
            )
            tasks.append(task)
        
        self.stdout.write(f'Created {len(tasks)} demo tasks')
        return tasks

    def _create_demo_messages(self, admin_user, client_users, worker_users):
        """Create demo messages."""
        try:
            from messaging.models import Message, MessageThread
        except ImportError:
            self.stdout.write('Messaging app not available - skipping messages')
            return []
        
        messages = []
        
        # Create some demo message threads
        for i, client in enumerate(client_users[:2]):  # Create messages for first 2 clients
            # Client to admin message
            message = Message.objects.create(
                sender=client,
                recipient=admin_user,
                subject=f'Demo: Question sur mon devis #{i+1}',
                content=f'<p>Bonjour,</p><p>J\'ai une question concernant mon devis. Pourriez-vous me rappeler ?</p><p>Cordialement,<br>{client.get_full_name()}</p>',
            )
            messages.append(message)
            
            # Admin response
            response = Message.objects.create(
                sender=admin_user,
                recipient=client,
                subject=f'Re: Demo: Question sur mon devis #{i+1}',
                content=f'<p>Bonjour {client.first_name},</p><p>Merci pour votre message. Je vous rappelle dans la journée pour discuter de votre devis.</p><p>Cordialement,<br>L\'équipe NetExpress</p>',
            )
            messages.append(response)
        
        # Worker to admin messages
        for worker in worker_users:
            message = Message.objects.create(
                sender=worker,
                recipient=admin_user,
                subject='Demo: Rapport de mission',
                content=f'<p>Bonjour,</p><p>Mission terminée avec succès. Le client était très satisfait.</p><p>Cordialement,<br>{worker.get_full_name()}</p>',
            )
            messages.append(message)
        
        self.stdout.write(f'Created {len(messages)} demo messages')
        return messages

    def _print_summary(self, admin_user, client_users, worker_users):
        """Print summary of created demo data."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('DEMO DATA SUMMARY')
        self.stdout.write('='*50)
        
        self.stdout.write(f'Admin User: {admin_user.username} (password: demo123)')
        
        self.stdout.write('\nClient Users:')
        for user in client_users:
            self.stdout.write(f'  - {user.username} ({user.email}) - password: demo123')
        
        self.stdout.write('\nWorker Users:')
        for user in worker_users:
            self.stdout.write(f'  - {user.username} ({user.email}) - password: demo123')
        
        self.stdout.write('\nPortal URLs:')
        self.stdout.write('  - Admin Portal: /admin-dashboard/')
        self.stdout.write('  - Client Portal: /client/')
        self.stdout.write('  - Worker Portal: /worker/')
        
        self.stdout.write('\n' + '='*50)