"""
Vues pour la génération et la consultation des factures. 
Compatibles avec factures/urls.py : 
 - create_invoice
 - download
 - archive
"""

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from django.conf import settings
from devis.models import Quote
from devis.services import create_invoice_from_quote, QuoteAlreadyInvoicedError, QuoteStatusError
from . models import Invoice
from core.services. email_service import PremiumEmailService
from core.decorators import admin_portal_required


@admin_portal_required
def create_invoice(request, quote_id:  int):
    """
    Crée une facture à partir d'un devis existant. 

    Utilise le service create_invoice_from_quote de l'app devis
    puis génère immédiatement le PDF. 
    """
    quote = get_object_or_404(Quote, pk=quote_id)
    
    try:
        # Utiliser le service de l'app devis pour créer la facture
        result = create_invoice_from_quote(quote)
        invoice = result.invoice
        messages.success(request, f"La facture {invoice.number} a été créée avec succès.")
    except QuoteAlreadyInvoicedError:
        messages. error(request, "Ce devis a déjà été facturé.")
        return redirect(reverse("factures:archive"))
    except QuoteStatusError as e:
        messages.error(request, f"Erreur lors de la création de la facture :  {str(e)}")
        return redirect(reverse("factures: archive"))
    except Exception as e:
        messages. error(request, f"Erreur lors de la création de la facture :  {str(e)}")
        return redirect(reverse("factures: archive"))

    # Générer et attacher le PDF premium à partir du modèle Django. 
    # Recalculer les totaux avant la génération pour s'assurer que le
    # document reflète les dernières valeurs.
    try:
        invoice.compute_totals()
        invoice.generate_pdf(attach=True)
        # Envoi immédiat de la facture au client (PDF en pièce jointe)
        PremiumEmailService().send_invoice_notification(invoice)
        # Marquer la facture comme envoyée
        if hasattr(invoice, "status"):
            invoice.status = Invoice. InvoiceStatus.SENT
            invoice.save(update_fields=["status"])
    except Exception as e:
        messages.error(
            request,
            f"La facture a été créée mais l'envoi e‑mail a échoué : {str(e)}",
        )
    
    # Avertir si la facture n'a pas de lignes
    if not invoice.invoice_items.exists():
        messages.warning(request, "La facture a été créée mais elle ne contient aucune ligne.")
    
    return redirect(reverse("factures: archive"))


@admin_portal_required
def download_invoice(request, pk: int):
    """
    Retourne le PDF de la facture.  Compatible Django 5. 
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    if not invoice.pdf: 
        raise Http404("Cette facture n'a pas encore de PDF généré.")

    return FileResponse(invoice.pdf. open("rb"), filename=invoice.pdf.name, as_attachment=False)


@admin_portal_required
def archive(request):
    """
    Affiche toutes les factures avec lien vers téléchargement PDF.
    """
    invoices = Invoice.objects.exclude(pdf="").order_by("-issue_date", "-number")
    return render(request, "factures/archive. html", {"invoices": invoices})
