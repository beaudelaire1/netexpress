"""
Vues pour la génération et la consultation des factures.
Compatibles avec factures/urls.py :
 - create_invoice
 - download
 - archive
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from django.conf import settings
from devis.models import Quote
from devis.services import create_invoice_from_quote
from .models import Invoice
from core.services.email_service import PremiumEmailService

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
        # Envoi immédiat de la facture au client (PDF en pièce jointe)
        PremiumEmailService().send_invoice_notification(invoice_model)
        # Marquer la facture comme envoyée (si le champ existe)
        try:
            if hasattr(invoice_model, "status"):
                invoice_model.status = Invoice.InvoiceStatus.SENT
                invoice_model.save(update_fields=["status"])
        except Exception:
            pass
    except Exception as e:
        messages.error(
            request,
            f"La facture a été créée mais l'envoi e‑mail a échoué : {str(e)}",
        )
    # Warn if invoice has no line items
    if not invoice_model.invoice_items.exists():
        messages.warning(request, "La facture a été créée mais elle ne contient aucune ligne.")
    return redirect(reverse("factures:archive"))


@staff_member_required
def download_invoice(request, pk: int):
    """
    Retourne le PDF de la facture. Compatible Django 5.
    Si le fichier PDF n'existe pas ou n'est pas accessible (système éphémère),
    le régénère à la volée.
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Vérifier si le PDF existe et est accessible
    pdf_exists = False
    if invoice.pdf:
        try:
            # Tenter d'ouvrir le fichier pour vérifier qu'il existe réellement
            invoice.pdf.open("rb")
            invoice.pdf.close()
            pdf_exists = True
        except (FileNotFoundError, OSError, IOError):
            # Le fichier n'existe pas (système éphémère) ou n'est pas accessible
            pdf_exists = False
    
    # Si le PDF n'existe pas, le régénérer à la volée
    if not pdf_exists:
        try:
            # Régénérer le PDF sans l'attacher (pour éviter d'écrire sur le système éphémère)
            pdf_bytes = invoice.generate_pdf(attach=False)
            # Construire le nom du fichier
            filename = f"{invoice.number or 'facture'}.pdf"
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except Exception as e:
            raise Http404(f"Impossible de générer le PDF de la facture : {str(e)}")
    
    return FileResponse(invoice.pdf.open("rb"), filename=invoice.pdf.name, as_attachment=False)


@staff_member_required
def archive(request):
    """
    Affiche toutes les factures avec lien vers téléchargement PDF.
    """
    invoices = Invoice.objects.exclude(pdf="").order_by("-issue_date", "-number")
    return render(request, "factures/archive.html", {"invoices": invoices})
