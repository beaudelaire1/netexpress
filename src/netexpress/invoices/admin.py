"""
Configuration de l’administration pour l’app ``invoices`` (legacy).

Cette configuration expose le modèle ``Invoice`` dans l'interface d’administration
et ajoute une action personnalisée permettant de générer des fichiers PDF.
Depuis la refonte de 2025, l’action gère explicitement l’absence de
ReportLab : les factures dont la génération échoue affichent un
message d’avertissement plutôt que de provoquer une erreur.  Il est
recommandé de migrer vers l’app ``factures`` pour bénéficier des dernières
fonctionnalités.
"""

from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "quote", "amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("number", "quote__name")
    actions = ["generate_pdfs"]

    def generate_pdfs(self, request, queryset):
        """Action admin pour générer les fichiers PDF des factures sélectionnées."""
        count = 0
        failed = 0
        for invoice in queryset:
            if not invoice.pdf:
                # Si le numéro n'est pas défini, en générer un
                if not invoice.number:
                    invoice.number = invoice.generate_number()
                try:
                    invoice.generate_pdf()
                    invoice.save()
                    count += 1
                except ImportError:
                    failed += 1
        if count:
            self.message_user(request, f"{count} facture(s) convertie(s) en PDF.")
        if failed:
            self.message_user(
                request,
                "La génération de certains PDFs a échoué car ReportLab n'est pas installé.",
                level="warning",
            )
    generate_pdfs.short_description = "Générer les PDF pour les factures sélectionnées"