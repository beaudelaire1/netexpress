"""
Configuration de l'administration pour l'app ``contact`` (2025).

Cette configuration enregistre le modèle ``Message`` et fournit une vue
en liste filtrable et recherchable par sujet, nom ou e‑mail.  Le champ
``processed`` est éditable directement depuis la liste afin de marquer
les messages comme traités.  La refonte de 2025 a rendu le champ
téléphone obligatoire et harmonisé les couleurs de l’interface avec
les autres apps.  Les visuels utilisés sur les pages du site proviennent
d’Unsplash et sont sans droits【668280112401708†L16-L63】.
"""

from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "topic", "created_at", "processed")
    list_filter = ("topic", "processed", "created_at")
    search_fields = ("full_name", "email", "body")
    list_editable = ("processed",)
    readonly_fields = ("created_at", "ip")

    # Ajout d'un commentaire de code pour documenter l'amélioration :
    # Depuis 2025, le champ téléphone du formulaire est requis.  Cette
    # configuration admin reste inchangée mais reflète l'état actuel du modèle.