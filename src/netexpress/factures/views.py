"""
Vues pour la génération et la livraison de factures.

Ces vues sont protégées par le décorateur ``staff_member_required`` afin
d'empêcher l'accès public.  Elles permettent de créer une facture à partir
d'un devis et de télécharger le PDF généré.

En 2025, la génération des PDFs a été encapsulée dans un bloc ``try/except``
afin d'attraper explicitement l'absence de la bibliothèque ReportLab.  Si
cette dépendance n'est pas installée, un message clair est affiché dans
l'administration et aucune erreur serveur n'est levée.
"""

from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect, render
from django.http import FileResponse, Http404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse

from devis.models import Quote
from .models import Invoice, InvoiceItem


@staff_member_required
def create_invoice(request, quote_id):
    """
    Créer une facture pour le devis donné.

    Si une facture existe déjà pour ce devis, elle est réutilisée.  Sinon
    une nouvelle facture est créée avec un montant par défaut.  Le PDF est
    généré avant la redirection vers l'URL de téléchargement de la facture.
    """
    quote = get_object_or_404(Quote, pk=quote_id)
    # Vérifier si une facture existe déjà pour ce devis
    invoice, created = Invoice.objects.get_or_create(quote=quote)
    if created:
        # Copier les lignes du devis vers la facture
        for q_item in quote.quote_items.all():
            InvoiceItem.objects.create(
                invoice=invoice,
                description=q_item.description or (q_item.service.title if q_item.service else ""),
                quantity=q_item.quantity,
                unit_price=q_item.unit_price,
                tax_rate=q_item.tax_rate,
            )
        # Calculer les totaux depuis les items
        invoice.compute_totals()
        # Par défaut, fixer la date d'échéance à 30 jours après l'émission
        from datetime import timedelta
        invoice.due_date = invoice.issue_date + timedelta(days=30)
        invoice.save()
    # Générer ou regénérer le PDF (toujours recalculer au préalable)
    invoice.compute_totals()
    try:
        invoice.generate_pdf()
        invoice.save()
    except ImportError as e:
        # La bibliothèque ReportLab n'est pas disponible : informer l'utilisateur et
        # rediriger vers l'admin sans tenter le téléchargement.
        messages.error(
            request,
            "La génération de PDF nécessite l'installation de ReportLab. "
            "Veuillez installer la dépendance ou désactiver cette fonctionnalité."
        )
        return redirect(reverse("admin:index"))
    return redirect(reverse("factures:download", args=[invoice.pk]))


@staff_member_required
def download_invoice(request, pk):
    """
    Servir le fichier PDF associé à la facture.

    Lève une 404 si la facture n'existe pas ou si le PDF n'a pas été généré.
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    if not invoice.pdf:
        raise Http404("Cette facture n'a pas encore été générée.")
    # Servir le PDF en ligne pour qu'il s'ouvre dans le navigateur
    response = FileResponse(
        invoice.pdf.open("rb"), filename=invoice.pdf.name, as_attachment=False
    )
    return response


# -----------------------------------------------------------------------------
# Archive des factures
# -----------------------------------------------------------------------------


@staff_member_required
def archive(request):
    """Affiche la liste des factures générées avec un lien vers leur PDF.

    Cette vue est accessible uniquement aux membres du staff (administrateurs).
    Elle permet de consulter rapidement l'ensemble des factures (et leurs
    documents PDF) depuis un même endroit.  Les factures sans PDF sont
    filtrées.
    """
    invoices = Invoice.objects.exclude(pdf="").order_by("-issue_date", "-number")
    return render(request, "factures/archive.html", {"invoices": invoices})
