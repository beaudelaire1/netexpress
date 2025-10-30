"""
Configuration de l’administration pour le modèle ``Quote`` (app legacy ``quotes``).

Cette configuration expose les demandes de devis dans l’administration Django.
Le personnel peut filtrer par statut et rechercher des clients par nom ou
e‑mail.  Dans la refonte de 2025, l’interface met l’accent sur une
navigation claire et rappelle que les images visibles sur le site proviennent
de sources libres de droits【668280112401708†L16-L63】.  Jazzmin appliquera
automatiquement son style si installé, sinon l’interface reste
fonctionnelle avec le thème par défaut.
"""

from django.contrib import admin
from .models import Quote


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "service")
    date_hierarchy = "created_at"