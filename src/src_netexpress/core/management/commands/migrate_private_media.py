"""Copy private documents from their former storage; dry-run unless --apply."""
import hashlib
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError
from core.private_files import private_file_fields
from core.storage import private_storage


def digest(file):
    result = hashlib.sha256()
    for chunk in file.chunks():
        result.update(chunk)
    return result.hexdigest()


class Command(BaseCommand):
    help = "Copie et vérifie les pièces privées existantes, sans supprimer les originaux."

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=["local", "cloudinary"], required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        if options["source"] == "local":
            source = FileSystemStorage(location=settings.MEDIA_ROOT)
        else:
            from cloudinary_storage.storage import MediaCloudinaryStorage
            source = MediaCloudinaryStorage()
        count = missing = 0
        for model, field in private_file_fields():
            if model._meta.app_label == "accounting":
                continue  # New files were never in public storage.
            manager = getattr(model, "all_objects", model._default_manager)
            for name in manager.exclude(**{field: ""}).exclude(**{field: None}).values_list(field, flat=True).iterator():
                if private_storage.exists(name):
                    continue
                if not source.exists(name):
                    missing += 1
                    self.stderr.write(f"Source absente : {model._meta.label} / {name}")
                    continue
                count += 1
                if options["apply"]:
                    with source.open(name, "rb") as old:
                        expected = digest(old)
                        old.seek(0)
                        saved = private_storage.save(name, old)
                    with private_storage.open(saved, "rb") as new:
                        if saved != name or digest(new) != expected:
                            raise CommandError(f"Vérification échouée : {name}")
        self.stdout.write(f"{count} fichiers {'copiés et vérifiés' if options['apply'] else 'à copier (simulation)'}, {missing} sources absentes.")
        self.stdout.write("Après sauvegarde et validation : retirez les originaux privés du stockage public et invalidez le CDN.")
        if missing:
            raise CommandError("Des pièces sont manquantes. Ne pas ouvrir la production avant rapprochement.")
