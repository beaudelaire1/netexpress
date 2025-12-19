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
from .models import Invoice

# Use the simplified invoicing service from the devis app.  The
# ``create_invoice_from_quote`` function creates a new invoice and
# returns an object containing the invoice and the originating quote.
from devis.services import create_invoice_from_quote


@staff_member_required
def create_invoice(request, quote_id: int):
    """
    Crée une facture à partir d'un devis existant.

    Logique explicite : on passe par la Service Layer (devis.services.create_invoice_from_quote),
    puis on génère immédiatement le PDF.
    """
    # Retrieve the quote instance and create the invoice using the
    # simplified service.  We wrap the logic in a try/except block to
    # handle business rule violations (e.g. quote not accepted or already invoiced).
    quote = get_object_or_404(Quote, pk=quote_id)
    try:
        # Le service create_invoice_from_quote renvoie un objet avec l'attribut
        # ``invoice`` (instance du modèle Invoice) et ``quote``.
        result = create_invoice_from_quote(quote)
        invoice_model = result.invoice
        messages.success(request, f"La facture {invoice_model.number} a été créée avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la création de la facture : {str(e)}")
        return redirect(reverse("factures:archive"))

    # Calculate totals and generate the PDF using the built‑in model methods.
    try:
        invoice_model.compute_totals()
        invoice_model.generate_pdf(attach=True)
    except Exception as e:
        messages.error(request, f"La facture a été créée mais le PDF n'a pas pu être généré : {str(e)}")

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
