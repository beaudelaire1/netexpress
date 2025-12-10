#!/usr/bin/env python
import os
import sys


def main() -> None:
    """Point d’entrée des commandes Django."""
    # Module de settings à utiliser par défaut
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netexpress.settings.base")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifie que Django est bien installé "
            "dans ton environnement (venv) et que celui-ci est activé."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
