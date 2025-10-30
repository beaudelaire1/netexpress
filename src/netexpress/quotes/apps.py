"""
Configuration de l’application ``quotes`` (version héritée).

Cette app conserve les routes et modèles pour les demandes de devis en
anglais.  Elle a été mise à jour en 2025 pour exiger un numéro de
téléphone et pour utiliser des images libres de droits dans ses
templates.  La configuration ajoute également un ``verbose_name`` pour
l’interface d’administration.
"""

from django.apps import AppConfig


class QuotesConfig(AppConfig):
    """AppConfig personnalisé pour l’app de demandes de devis (legacy)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "quotes"
    verbose_name = "Demandes de devis (legacy)"