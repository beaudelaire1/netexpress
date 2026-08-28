from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Ancien provisionnement désactivé. Utiliser createsuperuser explicitement."

    def handle(self, *args, **options):
        raise CommandError("Aucun compte par défaut. Utilisez python manage.py createsuperuser dans un terminal administrateur.")
