"""
Configuration de l’administration pour les services et leurs tâches.

Ce module définit la manière dont les services et les tâches associées
s’affichent dans l’interface d’administration.  En 2025, nous avons
    modernisé la présentation : les illustrations des services peuvent
    être absentes, auquel cas des images locales (dossier ``static/img``)
    sont utilisées dans les pages publiques.  Cette configuration permet
    d’éditer les tâches directement en ligne pour faciliter la gestion des
    checklists.  Jazzmin, s’il est installé, se chargera de l’esthétique;
    sinon, le thème par défaut reste propre et fonctionnel.
"""

from django.contrib import admin
from .models import Category, Service, ServiceTask


class ServiceTaskInline(admin.TabularInline):
    model = ServiceTask
    extra = 1


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "unit_type", "description")
    list_filter = ("category", "is_active")
    search_fields = ("title", "description", "short_description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ServiceTaskInline]

# Register Category so administrators can manage top‑level categories.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    # Inclure l'icône dans le formulaire afin de pouvoir téléverser une image.
    fields = ("name", "slug", "icon")