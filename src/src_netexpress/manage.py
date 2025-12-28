#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    # Charger le .env uniquement si python-dotenv est installé (dev)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # En prod (Render), les variables sont déjà injectées

    # Utiliser dev par défaut pour le développement local
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "netexpress.settings.dev")
    )

    # Warning utile: en local, on se retrouve souvent en prod par erreur via variable d'environnement.
    # On n'ecrase rien ici, on alerte juste.
    if os.getenv("DJANGO_SETTINGS_MODULE") == "netexpress.settings.prod" and any(
        cmd in sys.argv for cmd in ("runserver", "shell", "check_brevo")
    ):
        print("[WARN] DJANGO_SETTINGS_MODULE=netexpress.settings.prod (tu voulais peut-etre dev ?)")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
