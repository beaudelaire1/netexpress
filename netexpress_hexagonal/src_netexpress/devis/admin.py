"""
Configuration de l'administration pour l'app ``devis``.

Les listes affichent les devis avec le numéro, le client, le service et le
statut.  On ajoute également le modèle ``Client`` pour gérer les fiches
clients depuis l'interface d'administration.  Les filtres et champs de
recherche facilitent la gestion commerciale.
"""

from django.contrib import admin

from .models import Client, Quote, QuoteItem
from tasks.services import EmailNotificationService


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
    actions = ["send_quotes", "convert_to_invoice"]

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

    def send_quotes(self, request, queryset):
        """Action admin pour envoyer des devis par e‑mail aux clients.

        Pour chaque devis sélectionné cette action calcule les totaux,
        puis envoie un courriel simple récapitulant le devis.  Si le
        client ne possède pas d'adresse e‑mail aucune action n'est
        effectuée.  Les lignes de devis sont incluses dans le corps du
        message sous forme de liste.  Cette action ne génère pas de
        fichier PDF.  Pour des documents plus formels il est
        recommandé de convertir le devis en facture.
        """
        count = 0
        for quote in queryset:
            quote.compute_totals()
            client = quote.client
            if not client or not client.email:
                continue
            lines = []
            for item in quote.items:
                label = item.description or (item.service.title if item.service else "")
                lines.append(
                    f"- {label} : {item.quantity} × {item.unit_price} € HT (TVA {item.tax_rate}%\n"
                    f"  = {item.total_ttc} € TTC)"
                )
            body = (
                f"Bonjour {client.full_name},\n\n"
                f"Merci de votre demande de devis. Voici le détail de votre proposition :\n"
                "\n".join(lines)
                + "\n\n"
                f"Total HT : {quote.total_ht} €\n"
                f"TVA : {quote.tva} €\n"
                f"Total TTC : {quote.total_ttc} €\n"
                + (f"Ce devis est valable jusqu'au {quote.valid_until.strftime('%d/%m/%Y')}.\n" if quote.valid_until else "")
                + "\nNous restons à votre disposition pour toute question."
            )
            EmailNotificationService.send(
                client.email,
                f"Votre devis {quote.number}",
                body,
            )
            count += 1
        self.message_user(request, f"{count} devis envoyé(s) par e‑mail.")
    send_quotes.short_description = "Envoyer les devis sélectionnés par e‑mail"

    def convert_to_invoice(self, request, queryset):
        """Convertir les devis sélectionnés en factures.

        Cette action crée une facture pour chaque devis sélectionné qui n'a pas
        encore été converti. Les lignes de devis sont copiées dans la facture.
        Après conversion, les totaux sont recalculés. Les factures créées sont
        enregistrées avec un numéro généré automatiquement.
        """
        from datetime import date
        from factures.models import Invoice, InvoiceItem  # type: ignore
        converted = 0
        for quote in queryset:
            # ne pas convertir s'il existe déjà une facture pour ce devis
            if hasattr(quote, "invoices") and quote.invoices.exists():
                continue
            # Créer la facture liée au devis
            invoice = Invoice.objects.create(
                quote=quote,
                issue_date=date.today(),
                # Par défaut, une facture convertie est considérée comme envoyée.
                # On n'utilise plus le statut "demo" afin que le filigrane
                # indique "FACTURE" et non "DEVIS" sur le PDF.
                status="sent",
            )
            # Copier chaque ligne de devis dans la facture
            for qitem in quote.items:
                description = qitem.description or (qitem.service.title if qitem.service else "")
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=description,
                    quantity=qitem.quantity,
                    unit_price=qitem.unit_price,
                    tax_rate=qitem.tax_rate,
                )
            # Calculer les totaux et enregistrer
            invoice.compute_totals()
            invoice.save()
            converted += 1
        if converted:
            self.message_user(request, f"{converted} devis converti(s) en facture avec succès.")
        else:
            self.message_user(request, "Aucun devis n'a été converti (facture déjà existante ou sélection vide).")
    convert_to_invoice.short_description = "Convertir en facture"