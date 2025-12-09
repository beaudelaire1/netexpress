"""
Vues pour la génération et la consultation des factures.
Compatibles avec factures/urls.py :
 - create_invoice
 - download
 - archive
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from devis.models import Quote
from .models import Invoice


@staff_member_required
def create_invoice(request, quote_id: int):
    """
    Créer une facture à partir d'un devis existant.
    Utilise Invoice.create_from_quote si elle existe, sinon fallback simple.
    """

    quote = get_object_or_404(Quote, pk=quote_id)

    # Utilise ta logique métier si elle existe dans ton modèle
    if hasattr(Invoice, "create_from_quote") and callable(getattr(Invoice, "create_from_quote")):
        invoice = Invoice.create_from_quote(quote)
    else:
        invoice = Invoice.objects.create(quote=quote)

    # Génération PDF si supporté
    if hasattr(invoice, "generate_pdf") and callable(getattr(invoice, "generate_pdf")):
        try:
            invoice.generate_pdf(attach=True)
        except Exception:
            pass

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
