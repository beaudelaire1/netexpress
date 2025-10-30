"""
Vues pour la génération et la livraison de factures (app ``invoices``).

Seuls les utilisateurs staff peuvent accéder à ces vues.  Elles
permettent de créer une facture à partir d’un devis et de télécharger
les factures existantes.  En 2025, la création de facture est entourée
d’un bloc ``try/except`` afin d’attraper l’absence éventuelle de la
bibliothèque ReportLab et d’afficher un message clair plutôt que de
planter.
"""

from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse, Http404
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.contrib import messages  # pour afficher des messages d'erreur

from quotes.models import Quote
from .models import Invoice


@staff_member_required
def create_invoice(request, quote_id):
    """
    Create an invoice for the given quote.

    If an invoice already exists for this quote, it is reused.  Otherwise a new
    Invoice is created with a default amount.  The PDF is generated and the
    user is redirected to the invoice download URL.
    """
    quote = get_object_or_404(Quote, pk=quote_id)
    invoice, created = Invoice.objects.get_or_create(quote=quote, defaults={"amount": Decimal("0.00")})
    if not invoice.number:
        invoice.number = invoice.generate_number()
    # Use a default amount if not specified; in a real application, you would compute
    # this from the quote details or a pricing engine.
    if not invoice.amount or invoice.amount == Decimal("0.00"):
        invoice.amount = Decimal("100.00")  # placeholder value
    try:
        invoice.generate_pdf()
        invoice.save()
    except ImportError:
        # ReportLab n'est pas disponible : informer l'utilisateur via un message flash
        messages.error(
            request,
            "La génération de PDF nécessite la bibliothèque ReportLab. "
            "Installez la dépendance ou désactivez cette fonctionnalité."
        )
        return redirect(reverse("admin:index"))
    return redirect(reverse("invoices:download", args=[invoice.pk]))


@staff_member_required
def download_invoice(request, pk):
    """
    Serve the PDF file associated with the invoice.

    Raises 404 if the invoice does not exist or if the PDF hasn't been generated.
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    if not invoice.pdf:
        raise Http404("Cette facture n'a pas encore été générée.")
    response = FileResponse(invoice.pdf.open("rb"), filename=invoice.pdf.name, as_attachment=True)
    return response