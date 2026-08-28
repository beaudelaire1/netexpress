from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404

from accounts.portal import get_user_role
from .services.document_service import ClientDocumentService


def private_file_fields():
    from devis.models import Quote, QuotePhoto, QuoteRequestPhoto
    from factures.models import Invoice
    from messaging.models import EmailMessage
    from accounting.models import AccountingDocument, SupplierInvoice
    from .models import ClientPortalDocument, ClientSubmittedDocument

    return [
        (Quote, "pdf"),
        (Invoice, "pdf"),
        (ClientPortalDocument, "file"),
        (ClientSubmittedDocument, "file"),
        (QuotePhoto, "image"),
        (QuoteRequestPhoto, "image"),
        (EmailMessage, "attachment"),
        (SupplierInvoice, "file"),
        (AccountingDocument, "file"),
    ]


@login_required
def download_private_document(request, name):
    role = get_user_role(request.user)
    admin = role in {"admin_business", "admin_technical"}
    accountant = role == "accountant" and request.user.profile.has_verified_email

    for model, field in private_file_fields():
        manager = getattr(model, "all_objects", model._default_manager)
        document = manager.filter(**{field: name}).first()
        if not document:
            continue

        kind = model.__name__
        allowed = admin

        if kind == "Invoice":
            from accounting.services import issued_invoices

            allowed |= (
                accountant
                and issued_invoices().filter(pk=document.pk).exists()
            ) or ClientDocumentService.can_access_invoice(request.user, document)
        elif kind == "SupplierInvoice":
            from accounting.services import complete_purchases

            allowed |= accountant and complete_purchases(
                model.objects.filter(pk=document.pk)
            ).exists()
        elif kind == "AccountingDocument":
            allowed |= accountant
        elif kind == "Quote":
            from accounting.services import shared_quotes

            allowed |= (
                accountant and shared_quotes().filter(pk=document.pk).exists()
            ) or ClientDocumentService.can_access_quote(request.user, document)
        elif kind == "ClientPortalDocument":
            allowed |= ClientDocumentService.can_access_portal_document(
                request.user, document
            )
        elif kind == "ClientSubmittedDocument":
            allowed |= document.client_user_id == request.user.pk
        elif kind == "QuotePhoto":
            allowed |= ClientDocumentService.can_access_quote(
                request.user, document.quote
            )

        if not allowed:
            raise Http404("Document introuvable.")

        file = getattr(document, field)
        try:
            response = FileResponse(
                file.open("rb"),
                as_attachment=True,
                filename=Path(name).name,
            )
        except (OSError, ValueError):
            raise Http404("Pièce indisponible. Contactez l’administrateur.")

        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    raise Http404("Document introuvable.")
