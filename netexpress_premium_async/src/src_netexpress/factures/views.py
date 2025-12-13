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

from devis.models import Quote
from devis.services import create_invoice_from_quote
from .models import Invoice


@staff_member_required
def create_invoice(request, quote_id: int):
    """
    Crée une facture à partir d'un devis existant.

    Logique explicite : on passe par la Service Layer (devis.services.create_invoice_from_quote),
    puis on génère immédiatement le PDF.
    """
    quote = get_object_or_404(Quote, pk=quote_id)

    try:
        invoice = create_invoice_from_quote(quote)
        messages.success(request, f"La facture {invoice.number} a été créée avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la création de la facture : {str(e)}")
        return redirect(reverse("factures:archive"))

    try:
        invoice.generate_pdf(attach=True)
    except Exception as e:
        messages.error(request, f"La facture a été créée mais le PDF n'a pas pu être généré : {str(e)}")

    if not invoice.invoice_items.exists():
        messages.warning(request, "La facture a été créée mais elle ne contient aucune ligne.")

    return redirect(reverse("factures:archive"))

    # Génération du PDF (explicite)
    try:
        invoice.generate_pdf(attach=True)
    except Exception as e:
        messages.error(request, f"La facture a été créée mais le PDF n'a pas pu être généré : {str(e)}")
    # Vérifier si la facture est vide (aucune ligne copiée)
    if invoice and not invoice.invoice_items.exists():
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
