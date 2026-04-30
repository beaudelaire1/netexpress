"""
Crée le superuser par défaut si aucun superuser n'existe.
Utilisé au démarrage en production pour garantir un accès admin.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Crée le superuser par défaut si aucun superuser n'existe en base."

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS("Un superuser existe déjà. Rien à faire."))
            return

        User.objects.create_superuser(
            username="luxama_admin",
            email="admin@nettoyageexpresse.fr",
            password="Clo-admin@973*",
        )
        self.stdout.write(self.style.SUCCESS("Superuser 'luxama_admin' créé avec succès."))
