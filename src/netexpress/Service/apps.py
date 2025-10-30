"""
Configuration de l'application ``Service``.

Cette configuration fournit un ``verbose_name`` explicite afin d’afficher
un libellé convivial dans l’interface d’administration.  Le nom de
l'application reste ``Service`` pour des raisons de compatibilité mais
les modèles et vues sont alignés sur la nouvelle charte de NetExpress.
"""

from django.apps import AppConfig


class ServiceConfig(AppConfig):
    """AppConfig personnalisé pour le catalogue de services historique."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Service'
    # Ajout d'un libellé lisible dans l'admin
    verbose_name = "Catalogue des services (hérité)"
