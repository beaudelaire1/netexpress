"""
Vues pour la génération et la consultation des factures.
Compatibles avec factures/urls.py :
 - create_invoice
 - download
 - archive
"""

import logging

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from devis.models import Quote
from devis.services import (
    QuoteAlreadyInvoicedError,
    QuoteStatusError,
    create_invoice_from_quote,
)
from core.services.email_service import PremiumEmailService
from core.decorators import admin_portal_required
from .models import Invoice


logger = logging.getLogger(__name__)


@admin_portal_required
@require_POST
def create_invoice(request, quote_id: int):
    """Crée une facture à partir d'un devis existant et prépare son PDF."""
    quote = get_object_or_404(Quote, pk=quote_id)

    try:
        result = create_invoice_from_quote(quote)
        invoice = result.invoice
        messages.success(request, f"La facture {invoice.number} a été créée avec succès.")
    except QuoteAlreadyInvoicedError:
        messages.error(request, "Ce devis a déjà été facturé.")
        return redirect(reverse("factures:archive"))
    except QuoteStatusError as exc:
        messages.error(request, f"Erreur lors de la création de la facture : {exc}")
        return redirect(reverse("factures:archive"))
    except Exception as exc:
        logger.exception("Échec de création de facture depuis le devis %s", quote.pk)
        messages.error(request, f"Erreur lors de la création de la facture : {exc}")
        return redirect(reverse("factures:archive"))

    # Générer et attacher le PDF premium à partir du modèle Django.
    # La facture reste créée si la génération ou l'envoi échoue : le PDF
    # pourra être régénéré à la demande via download_invoice().
    try:
        invoice.compute_totals()
        invoice.generate_pdf(attach=True)

        if not PremiumEmailService().send_invoice_notification(invoice):
            raise RuntimeError("Envoi non confirmé par le service email.")

        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save(update_fields=["status"])
    except Exception as exc:
        logger.exception(
            "Facture %s créée mais génération PDF ou envoi e-mail incomplet",
            invoice.pk,
        )
        messages.error(
            request,
            f"La facture a été créée mais sa préparation ou son envoi a échoué : {exc}",
        )

    if not invoice.invoice_items.exists():
        messages.warning(request, "La facture a été créée mais elle ne contient aucune ligne.")

    return redirect(reverse("factures:archive"))


@admin_portal_required
def download_invoice(request, pk: int):
    """Retourne le PDF de la facture, en le générant à la demande si nécessaire."""
    invoice = get_object_or_404(Invoice, pk=pk)

    if not invoice.pdf:
        try:
            # Ne pas produire silencieusement un document vide : une facture
            # sans lignes indique un problème de création/conversion à corriger.
            if not invoice.invoice_items.exists():
                raise ValueError("la facture ne contient aucune ligne")

            invoice.compute_totals()
            invoice.generate_pdf(attach=True)
            invoice.refresh_from_db(fields=["pdf"])
        except Exception as exc:
            logger.exception("Impossible de générer le PDF de la facture %s", invoice.pk)
            raise Http404(
                "Le PDF de cette facture n'existe pas encore et sa génération a échoué."
            ) from exc

    if not invoice.pdf:
        raise Http404("Le PDF de cette facture n'a pas pu être généré.")

    try:
        return FileResponse(
            invoice.pdf.open("rb"),
            filename=invoice.pdf.name,
            as_attachment=False,
            content_type="application/pdf",
        )
    except (FileNotFoundError, OSError) as exc:
        logger.exception("Fichier PDF introuvable pour la facture %s", invoice.pk)
        raise Http404("Le fichier PDF associé à cette facture est introuvable.") from exc


@admin_portal_required
def archive(request):
    """Affiche toutes les factures disposant déjà d'un PDF attaché."""
    invoices = Invoice.objects.exclude(pdf="").order_by("-issue_date", "-number")
    return render(request, "factures/archive.html", {"invoices": invoices})
