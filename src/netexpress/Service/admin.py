"""
Configuration de l'administration pour le catalogue de services (version héritée).

Cette classe expose le modèle ``Service`` dans l’administration Django et
ajoute quelques colonnes et filtres pour améliorer l’ergonomie.  Depuis
la refonte de 2025, les services utilisent des images libres de droits
provenant d’Unsplash lorsque aucune photo n’est uploadée, et les slugs
sont générés automatiquement.  L'interface reste compatible avec
Jazzmin si celui‑ci est installé, mais fonctionne également avec le thème
standard de Django.  Les champs modifiés (titre, prix, durée, actif)
permettent aux administrateurs de gérer facilement le catalogue.
"""

from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "base_price", "duration_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "description", "short_description")
    prepopulated_fields = {"slug": ("title",)}
