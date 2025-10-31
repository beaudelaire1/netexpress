"""
Configuration de l'administration pour l'app ``factures``.

Cette configuration permet de générer des PDF pour les factures sélectionnées
directement depuis la liste dans l'admin et de visualiser les attributs
principaux (numéro, devis associé, montant, date).
"""

from django.contrib import admin
from django.utils.html import format_html
from django.core.files.base import ContentFile

from .models import Invoice, InvoiceItem
from tasks.services import EmailNotificationService


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "quote", "status", "issue_date", "total_ttc", "pdf_link")
    list_filter = ("status", "issue_date")
    search_fields = ("number", "quote__client__full_name")
    readonly_fields = ("total_ht", "tva", "total_ttc", "issue_date", "created_at")
    actions = ["generate_pdfs", "send_invoices"]

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

    def pdf_link(self, obj: Invoice) -> str:
        """Return an HTML link to download the PDF if it exists."""
        if obj.pdf:
            return format_html(
                "<a href='{}' target='_blank'>Ouvrir</a>",
                obj.pdf.url,
            )
        return "–"
    pdf_link.short_description = "PDF"

    def send_invoices(self, request, queryset):
        """Action admin to send selected invoices by email.

        For each selected invoice this action recalculates totals,
        generates a fresh PDF, saves it and emails it to the client if
        an email address is available.  The email body summarises the
        invoice amount and due date and includes the PDF as an
        attachment.  Errors during sending are logged but do not stop
        processing of subsequent invoices.
        """
        count = 0
        for invoice in queryset:
            # Toujours recalculer les totaux et générer un PDF à jour (sans l'attacher directement)
            invoice.compute_totals()
            pdf_content = invoice.generate_pdf(attach=False)

            # Déterminer un nom de fichier simple pour le PDF
            base_filename = f"{invoice.number}.pdf"
            if not invoice.pdf:
                # Aucune pièce jointe existante : enregistrer le PDF avec le nom de base
                invoice.pdf.save(base_filename, ContentFile(pdf_content), save=True)
            else:
                # Une pièce jointe existe déjà : utiliser uniquement le nom de fichier
                # (pas de répertoire "factures/"), afin d'éviter la duplication
                from os.path import basename
                name_on_field = basename(invoice.pdf.name) or base_filename
                invoice.pdf.save(name_on_field, ContentFile(pdf_content), save=True)

            # Chercher l'adresse e‑mail du destinataire à partir du devis lié
            recipient = None
            if (
                invoice.quote
                and getattr(invoice.quote, "client", None)
                and getattr(invoice.quote.client, "email", None)
            ):
                recipient = invoice.quote.client.email

            # Envoyer l'e‑mail avec le PDF en pièce jointe si un destinataire est défini
            if recipient:
                subject = f"Votre facture {invoice.number}"
                body = (
                    f"Bonjour {invoice.quote.client.full_name},\n\n"
                    f"Veuillez trouver ci‑joint votre facture {invoice.number}.\n"
                    f"Montant TTC : {invoice.total_ttc} €\n"
                    f"Date d'émission : {invoice.issue_date.strftime('%d/%m/%Y')}\n"
                    + (
                        f"Échéance : {invoice.due_date.strftime('%d/%m/%Y')}\n"
                        if invoice.due_date
                        else ""
                    )
                    + "\nMerci de votre confiance."
                )
                EmailNotificationService.send(
                    recipient,
                    subject,
                    body,
                    attachments=[(base_filename, pdf_content)],
                )
                count += 1
        self.message_user(request, f"{count} facture(s) envoyée(s) par e‑mail.")
    send_invoices.short_description = "Envoyer les factures sélectionnées par e‑mail"