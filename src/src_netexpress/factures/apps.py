"""
Configuration de l’app ``factures``.

Cette application contient l’implémentation moderne de la gestion des
factures (factures multi-lignes, statuts, génération de PDF). Elle
remplace l’ancienne app ``invoices`` et adopte la charte graphique et
les conventions de 2025.
"""

from django.apps import AppConfig


class FacturesConfig(AppConfig):
    """AppConfig pour l’app moderne de facturation."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "factures"
    verbose_name = "Factures"

    def ready(self) -> None:
        # Les signaux font partie du cycle métier de facturation. Une erreur
        # d'import doit empêcher le démarrage plutôt que désactiver
        # silencieusement la finalisation automatique des factures.
        from . import signals  # noqa: F401
