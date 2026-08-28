"""Create a local-only accountant account, never a production backdoor."""
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile


class Command(BaseCommand):
    help = "Crée un compte cabinet de test sur la base locale uniquement (aucun email envoyé)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="cabinet_test")

    def handle(self, *args, **options):
        if (not settings.DEBUG or settings.SETTINGS_MODULE not in
                {"netexpress.settings.local", "netexpress.settings.test"} or
                settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3"):
            raise CommandError("Compte de test autorisé uniquement avec les settings local/test et SQLite "
                f"(module={settings.SETTINGS_MODULE}, DEBUG={settings.DEBUG}, "
                f"base={settings.DATABASES['default']['ENGINE']}).")
        User = get_user_model()
        username = options["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError("Ce compte existe déjà. Aucun mot de passe ni droit n’a été modifié.")
        password = secrets.token_urlsafe(21)
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=f"{username}@example.test",
                password=password, first_name="Cabinet", last_name="Test")
            profile = user.profile
            profile.role = Profile.ROLE_ACCOUNTANT
            profile.accounting_firm = "Cabinet de démonstration · test local"
            # This simulated verification is confined to local/test settings, without email delivery.
            profile.verified_email = user.email
            profile.email_verified_at = timezone.now()
            profile.save(update_fields=["role", "accounting_firm", "verified_email", "email_verified_at"])
        self.stdout.write(self.style.SUCCESS("Compte cabinet créé sur la base locale uniquement."))
        self.stdout.write(f"Identifiant : {username}")
        self.stdout.write(f"Mot de passe : {password}")
        self.stdout.write("Portail : /comptabilite/ — aucun accès administrateur.")
