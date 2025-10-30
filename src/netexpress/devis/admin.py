"""
Configuration de l'administration pour l'app ``devis``.

Les listes affichent les devis avec le numéro, le client, le service et le
statut.  On ajoute également le modèle ``Client`` pour gérer les fiches
clients depuis l'interface d'administration.  Les filtres et champs de
recherche facilitent la gestion commerciale.
"""

from django.contrib import admin

from .models import Client, Quote, QuoteItem


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "created_at")
    search_fields = ("full_name", "email", "phone")
    list_filter = ("created_at",)

    # Note : le champ téléphone est requis depuis la refonte 2025 pour assurer
    # une prise de contact fiable.  Aucune configuration supplémentaire n'est
    # nécessaire côté admin, cette information est renseignée lors de la création
    # du client.


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "status", "issue_date", "total_ttc")
    list_filter = ("status", "issue_date")
    search_fields = ("number", "client__full_name", "client__email")
    readonly_fields = ("created_at", "issue_date", "total_ht", "tva", "total_ttc")
    list_editable = ("status",)

    # Permettre l'édition des lignes de devis directement dans le devis
    class QuoteItemInline(admin.TabularInline):
        model = QuoteItem
        extra = 1
        fields = ("service", "description", "quantity", "unit_price", "tax_rate", "total_ht", "total_tva", "total_ttc")
        readonly_fields = ("total_ht", "total_tva", "total_ttc")

    inlines = [QuoteItemInline]

    def save_formset(self, request, form, formset, change):
        """Après sauvegarde des items, recalculer les totaux."""
        instances = formset.save()
        if formset.model is QuoteItem:
            form.instance.compute_totals()
        return instances