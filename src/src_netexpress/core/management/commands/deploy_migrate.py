"""Applique les migrations sous verrou PostgreSQL pour sécuriser les déploiements concurrents."""

from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection


# Verrou de session dédié aux migrations NetExpress. Il est automatiquement
# libéré par PostgreSQL si le conteneur ou la connexion disparaît brutalement.
MIGRATION_LOCK_ID = 624_982_731_047


class Command(BaseCommand):
    help = "Applique les migrations Django sous verrou consultatif PostgreSQL."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("deploy_migrate est réservé à PostgreSQL en production.")

        verbosity = options.get("verbosity", 1)
        self.stdout.write("Attente du verrou de migration PostgreSQL…")

        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", [MIGRATION_LOCK_ID])
            try:
                self.stdout.write("Verrou acquis. Application des migrations…")
                call_command(
                    "migrate",
                    interactive=False,
                    verbosity=verbosity,
                )
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_ID])

        self.stdout.write(self.style.SUCCESS("Migrations de production terminées."))
