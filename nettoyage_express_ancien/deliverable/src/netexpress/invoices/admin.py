"""
Admin configuration for invoices.

The invoice admin includes a custom action that allows staff members to
generate a PDF for selected invoices directly from the change list.  After
generating the PDF, the invoice object is saved so that the file field is
populated.
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
        """Admin action to generate PDF files for selected invoices."""
        count = 0
        for invoice in queryset:
            if not invoice.pdf:
                # If the invoice number hasn't been set yet, create one
                if not invoice.number:
                    invoice.number = invoice.generate_number()
                invoice.generate_pdf()
                invoice.save()
                count += 1
        self.message_user(request, f"{count} facture(s) convertie(s) en PDF.")
    generate_pdfs.short_description = "Générer les PDF pour les factures sélectionnées"