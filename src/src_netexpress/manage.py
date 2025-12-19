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

    # Ne JAMAIS forcer prod ici
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "netexpress.settings.prod")
    )

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
