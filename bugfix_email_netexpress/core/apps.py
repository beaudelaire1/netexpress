"""
Configuration de l'application ``core``.

La classe ``CoreConfig`` définit les métadonnées de l'app.  En 2025,
la configuration a été enrichie d'un ``verbose_name`` pour une meilleure
lisibilité dans l'admin.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = "Fonctionnalités génériques"
