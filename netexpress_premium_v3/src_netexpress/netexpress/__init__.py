"""
Package racine du projet NetExpress.

Ce package contient la configuration principale du framework Django
(paramètres, URL racine, WSGI/ASGI).  En l’absence de Django, le
fichier `manage.py` bascule automatiquement en mode statique pour
servir le répertoire `static_site`.  Tous les modules ont été mis à jour
en 2025 afin de respecter la localisation Europe/Bucharest et de
proposer une expérience cohérente sur l’ensemble des applications.
"""

# Celery app loading (so shared_task autodiscovery works with Django)
from .celery import app as celery_app  # noqa: F401
