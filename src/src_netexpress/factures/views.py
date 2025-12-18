"""
Vues pour la génération et la consultation des factures.
Compatibles avec factures/urls.py :
 - create_invoice
 - download
 - archive
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from django.conf import settings
from devis.models import Quote
from devis.services import create_invoice_from_quote
from .models import Invoice

# Import the hexagonal service layer and its adapters
from hexcore.services.invoice_service import InvoiceService
from django_orm.invoice_repository import DjangoInvoiceRepository
# Import the PDF generator from the adapter module.  Using a distinct
# module name prevents shadowing the external ``weasyprint`` library.
from weasyprint_adapter.pdf_generator import WeasyPrintGenerator


@staff_member_required
def create_invoice(request, quote_id: int):
    """
    Crée une facture à partir d'un devis existant.

    Logique explicite : on passe par la Service Layer (devis.services.create_invoice_from_quote),
    puis on génère immédiatement le PDF.
    """
    # Use the application service to orchestrate creation and PDF generation.
    quote = get_object_or_404(Quote, pk=quote_id)
    # Instanciation du service de facturation.  On spécifie
    # explicitement le template premium pour le générateur PDF.
    service = InvoiceService(
        invoice_repository=DjangoInvoiceRepository(),
        pdf_generator=WeasyPrintGenerator(template_name="pdf/invoice_premium.html"),
    )
    # First, create the invoice from the quote via the repository
    try:
        invoice_entity = service.create_invoice_from_quote(quote_id)
        # At this stage the invoice exists in the database and has a number
        messages.success(request, f"La facture {invoice_entity.number} a été créée avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la création de la facture : {str(e)}")
        return redirect(reverse("factures:archive"))

    # Look up the corresponding Invoice model to obtain its primary key.
    try:
        invoice_model = Invoice.objects.get(number=invoice_entity.number)
    except Invoice.DoesNotExist:
        messages.error(request, "La facture a été créée mais n'a pas pu être retrouvée en base.")
        return redirect(reverse("factures:archive"))

    # Générer et attacher le PDF premium à partir du modèle Django.  On
    # recalcul les totaux avant la génération pour s'assurer que le
    # document reflète les dernières valeurs.
    try:
        invoice_model.compute_totals()
        invoice_model.generate_pdf(attach=True)
    except Exception as e:
        messages.error(
            request,
            f"La facture a été créée mais le PDF n'a pas pu être généré : {str(e)}",
        )
    # Warn if invoice has no line items
    if not invoice_model.invoice_items.exists():
        messages.warning(request, "La facture a été créée mais elle ne contient aucune ligne.")
    return redirect(reverse("factures:archive"))


@staff_member_required
def download_invoice(request, pk: int):
    """
    Retourne le PDF de la facture. Compatible Django 5.
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    if not invoice.pdf:
        raise Http404("Cette facture n'a pas encore de PDF généré.")

    return FileResponse(invoice.pdf.open("rb"), filename=invoice.pdf.name, as_attachment=False)


@staff_member_required
def archive(request):
    """
    Affiche toutes les factures avec lien vers téléchargement PDF.
    """
    invoices = Invoice.objects.exclude(pdf="").order_by("-issue_date", "-number")
    return render(request, "factures/archive.html", {"invoices": invoices})
