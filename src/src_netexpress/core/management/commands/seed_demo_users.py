from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User

class Command(BaseCommand):
    help = "Crée des comptes de démonstration (client / ouvrier) + groupes."

    def handle(self, *args, **options):
        clients_group, _ = Group.objects.get_or_create(name="Clients")
        workers_group, _ = Group.objects.get_or_create(name="Ouvriers")

        def ensure_user(username: str, email: str, password: str, group: Group):
            user, created = User.objects.get_or_create(username=username, defaults={"email": email})
            if created:
                user.set_password(password)
                user.email = email
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Créé: {username} / {password}"))
            if group not in user.groups.all():
                user.groups.add(group)
            return user

        ensure_user("client", "client@example.com", "Client123!", clients_group)
        ensure_user("ouvrier", "ouvrier@example.com", "Ouvrier123!", workers_group)

        self.stdout.write(self.style.SUCCESS("OK. Groupes: Clients, Ouvriers."))
