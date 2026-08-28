from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from accounts.access import verified_client_id
from accounts.portal import get_user_role
from .services.document_service import ClientDocumentService


def private_file_fields():
    from devis.models import Quote, QuotePhoto, QuoteRequestPhoto
    from factures.models import Invoice
    from messaging.models import EmailMessage
    from accounting.models import AccountingDocument, SupplierInvoice
    from .models import ClientPortalDocument, ClientSubmittedDocument
    return [(Quote, "pdf"), (Invoice, "pdf"), (ClientPortalDocument, "file"),
            (ClientSubmittedDocument, "file"), (QuotePhoto, "image"),
            (QuoteRequestPhoto, "image"), (EmailMessage, "attachment"), (SupplierInvoice, "file"),
            (AccountingDocument, "file")]


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
            allowed |= (accountant and bool(document.issued_at)) or ClientDocumentService.can_access_invoice(request.user, document)
        elif kind in {"SupplierInvoice", "AccountingDocument"}:
            allowed |= accountant
        elif kind == "Quote":
            allowed |= (accountant and document.status in {"sent", "accepted", "rejected", "invoiced"}) or ClientDocumentService.can_access_quote(request.user, document)
        elif kind == "ClientPortalDocument":
            allowed |= ClientDocumentService.can_access_portal_document(request.user, document)
        elif kind == "ClientSubmittedDocument":
            allowed |= document.client_user_id == request.user.pk
        elif kind == "QuotePhoto":
            allowed |= ClientDocumentService.can_access_quote(request.user, document.quote)
        if not allowed:
            raise Http404("Document introuvable.")
        file = getattr(document, field)
        try:
            response = FileResponse(file.open("rb"), as_attachment=True, filename=Path(name).name)
        except (OSError, ValueError):
            raise Http404("PiÃ¨ce indisponible. Contactez lâ€™administrateur.")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    raise Http404("Document introuvable.")
