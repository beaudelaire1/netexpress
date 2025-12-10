"""
Configuration de l’app ``services`` (catalogue modernisé).

Cette app fournit la nouvelle implémentation du catalogue de services de
NetExpress.  Elle propose un design moderne, des vues filtrées et
sélectionne des illustrations libres de droits.  Le ``verbose_name`` est
défini pour une meilleure lisibilité dans l’interface d’administration.
"""

from django.apps import AppConfig


class ServicesConfig(AppConfig):
    """AppConfig pour le catalogue de services modernisé."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services'
    verbose_name = "Services"