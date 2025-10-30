"""
Configuration de l'administration pour l'app ``factures``.

Cette configuration permet de générer des PDF pour les factures sélectionnées
directement depuis la liste dans l'admin et de visualiser les attributs
principaux (numéro, devis associé, montant, date).
"""

from django.contrib import admin

from .models import Invoice, InvoiceItem


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "quote", "status", "issue_date", "total_ttc")
    list_filter = ("status", "issue_date")
    search_fields = ("number", "quote__client__full_name")
    readonly_fields = ("total_ht", "tva", "total_ttc", "issue_date", "created_at")
    actions = ["generate_pdfs"]

    class InvoiceItemInline(admin.TabularInline):
        model = InvoiceItem
        extra = 1
        fields = ("description", "quantity", "unit_price", "tax_rate", "total_ht", "total_tva", "total_ttc")
        readonly_fields = ("total_ht", "total_tva", "total_ttc")

    inlines = [InvoiceItemInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save()
        if formset.model is InvoiceItem:
            form.instance.compute_totals()
        return instances

    def generate_pdfs(self, request, queryset):
        """Action admin pour générer les fichiers PDF des factures sélectionnées."""
        count = 0
        for invoice in queryset:
            # recalculer les totaux avant génération
            invoice.compute_totals()
            invoice.generate_pdf()
            invoice.save()
            count += 1
        self.message_user(request, f"{count} facture(s) convertie(s) en PDF.")
    generate_pdfs.short_description = "Générer les PDF pour les factures sélectionnées"