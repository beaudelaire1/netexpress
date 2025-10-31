#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """
    Point d'entrée pour les tâches administratives.

    Ce script tente d'exécuter les commandes Django classiques.  Si Django
    n'est pas disponible (par exemple dans un environnement dépourvu de
    dépendances externes), une alternative minimaliste est proposée : un
    serveur HTTP basique est lancé afin de servir un site statique depuis
    ``static_site``.  Cela permet de tester l'interface utilisateur sans
    backend.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netexpress.settings.base")
    try:
        from django.core.management import execute_from_command_line
        # Si l'import réussit, on délègue à Django.
        execute_from_command_line(sys.argv)
        return
    except ImportError:
        # Django n'est pas installé : on propose un fallback.
        print("\033[33mAvertissement : Django n'est pas installé.\033[0m")
        print(
            "Un serveur HTTP basique va être lancé pour servir le contenu statique "
            "du dossier ‘static_site’. Placez vos fichiers HTML dans ce dossier "
            "pour les tester.\n"
        )
        try:
            from http.server import HTTPServer, SimpleHTTPRequestHandler
            from pathlib import Path
            # On se positionne dans le dossier static_site à côté de ce fichier.
            base_dir = Path(__file__).resolve().parent
            static_dir = base_dir / "static_site"
            if static_dir.is_dir():
                os.chdir(static_dir)
            else:
                # S'il n'existe pas encore, on crée un dossier et un fichier index.
                static_dir.mkdir(exist_ok=True)
                index = static_dir / "index.html"
                if not index.exists():
                    index.write_text(
                        "<h1>Bienvenue sur NetExpress</h1><p>Ce site statique est "
                        "servi faute de backend disponible.</p>",
                        encoding="utf-8",
                    )
                os.chdir(static_dir)
            httpd = HTTPServer(("0.0.0.0", 8000), SimpleHTTPRequestHandler)
            print("Serveur statique en cours d'exécution sur http://localhost:8000 …")
            httpd.serve_forever()
        except Exception as err:
            print("Impossible de lancer le serveur statique :", err)


if __name__ == '__main__':
    main()

