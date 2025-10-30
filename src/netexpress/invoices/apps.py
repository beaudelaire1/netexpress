"""
Configuration de l’app ``invoices`` (legacy).

Cette app regroupe les modèles et vues de factures héritées de l’ancienne
implémentation.  En 2025, elle a été mise à jour pour gérer
gracieusement l’absence de la bibliothèque ReportLab et pour clarifier
les numéros de facture.  Un ``verbose_name`` explicite est fourni pour
l’administration.
"""

from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    """AppConfig pour l’app ``invoices`` héritée."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "invoices"
    verbose_name = "Factures (legacy)"