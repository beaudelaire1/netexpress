import csv
import hashlib
import io
import json
from decimal import Decimal

from django.db.models import Q
from devis.models import Quote
from factures.models import Invoice
from .models import SupplierInvoice, AccountingActivity, AccountingDocument


def log_activity(user, action, target=""):
    AccountingActivity.objects.create(actor=user, action=action, target=str(target)[:200])


def invoice_fingerprint(invoice):
    client = invoice.quote.client if invoice.quote_id else None
    payload = {
        "number": invoice.number, "date": str(invoice.issue_date), "due": str(invoice.due_date),
        "ht": str(invoice.total_ht), "vat": str(invoice.tva), "ttc": str(invoice.total_ttc),
        "discount": str(invoice.discount), "credit": invoice.is_credit_note,
        "client": [client.pk, client.full_name, client.email, client.address_line, client.zip_code, client.city] if client else None,
        "items": [[i.description, str(i.quantity), str(i.unit_price), str(i.tax_rate)] for i in invoice.invoice_items.all()],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def is_reviewed(invoice):
    review = getattr(invoice, "accounting_review", None)
    return bool(review and review.fingerprint == invoice_fingerprint(invoice))


def issued_invoices():
    # An archived/soft-deleted issued document remains part of the accounting history.
    return Invoice.all_objects.filter(issued_at__isnull=False).select_related("quote__client", "accounting_review").prefetch_related("invoice_items")


def invoice_pdf_content(invoice):
    """Keep the original issued PDF; only render when no file was ever attached."""
    if not invoice.pdf:
        return invoice.generate_pdf(attach=False)
    with invoice.pdf.open("rb") as original:
        content = original.read(100 * 1024 * 1024 + 1)
    if not content.startswith(b"%PDF-") or len(content) > 100 * 1024 * 1024:
        raise ValueError("PDF original invalide ou supérieur à 100 Mo.")
    return content


def shared_quotes():
    return Quote.all_objects.filter(status__in=["sent", "accepted", "rejected", "invoiced"]).select_related("client").prefetch_related("quote_items")


def period_quotes(data):
    quotes = shared_quotes().filter(issue_date__range=(data["date_from"], data["date_to"]))
    if data.get("q"):
        quotes = quotes.filter(Q(number__icontains=data["q"]) | Q(client__full_name__icontains=data["q"]))
    return quotes


def quote_pdf_content(quote):
    # Render without calling Quote.generate_pdf(), which recalculates and saves totals.
    from core.services.document_generator import DocumentGenerator
    return DocumentGenerator.generate_quote_pdf(quote, attach=False)


def period_documents(data):
    sales = issued_invoices().filter(issue_date__range=(data["date_from"], data["date_to"]))
    # Undated deposits are visible by their upload date until the invoice date is known.
    purchases = SupplierInvoice.objects.filter(
        Q(issue_date__range=(data["date_from"], data["date_to"])) |
        Q(issue_date__isnull=True, created_at__date__range=(data["date_from"], data["date_to"]))
    )
    query = data.get("q", "")
    if query:
        sales = sales.filter(Q(number__icontains=query) | Q(quote__client__full_name__icontains=query))
        purchases = purchases.filter(Q(supplier_name__icontains=query) | Q(reference__icontains=query))
    return sales, purchases


def supporting_documents(data):
    documents = AccountingDocument.objects.filter(document_date__range=(data["date_from"], data["date_to"]))
    if data.get("q"):
        documents = documents.filter(Q(title__icontains=data["q"]) | Q(notes__icontains=data["q"]))
    return documents


def incomplete_purchases(purchases):
    return purchases.filter(Q(supplier_name="") | Q(reference="") | Q(issue_date__isnull=True) |
                            Q(total_ttc__isnull=True) | Q(vat_amount__isnull=True))


def csv_cell(value):
    text = str(value if value is not None else "")
    # Prevent spreadsheet formulas, including leading whitespace before =, +, -, @.
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def csv_content(sales, purchases, documents=()):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(["Type", "Numéro", "Tiers", "Date", "Échéance", "HT EUR", "TVA EUR", "TTC EUR", "Paiement", "Contrôle", "Note"])
    for invoice in sales:
        sign = Decimal(-1) if invoice.is_credit_note else Decimal(1)
        client = invoice.quote.client.full_name if invoice.quote_id else "Client non lié"
        review = getattr(invoice, "accounting_review", None)
        writer.writerow([csv_cell(v) for v in ["Avoir" if invoice.is_credit_note else "Vente", invoice.number, client,
            invoice.issue_date, invoice.due_date, *(format(sign * v, ".2f") for v in [invoice.total_ht, invoice.tva, invoice.total_ttc]),
            invoice.get_status_display(), "Comptabilisé" if is_reviewed(invoice) else "À vérifier", review.note if review else ""]])
    for purchase in purchases:
        writer.writerow([csv_cell(v) for v in ["Achat", purchase.reference, purchase.supplier_name, purchase.issue_date,
            purchase.due_date, *(format(v, ".2f") if v is not None else "" for v in [purchase.total_ht, purchase.vat_amount, purchase.total_ttc]),
            purchase.paid_on or "Non renseigné", "Comptabilisé" if purchase.reviewed_at else ("À vérifier" if purchase.is_complete else "À compléter"), purchase.notes]])
    for document in documents:
        writer.writerow([csv_cell(v) for v in [document.get_kind_display(), document.title, "", document.document_date,
            "", "", "", "", "", "Vérifié" if document.reviewed_at else "À vérifier", document.notes]])
    return stream.getvalue().encode("utf-8-sig")


def quotes_csv_content(quotes):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(["Devis", "Client", "Date", "Validité", "HT EUR", "TVA EUR", "TTC EUR", "Statut"])
    for quote in quotes:
        writer.writerow([csv_cell(v) for v in [quote.number, quote.client.full_name, quote.issue_date,
            quote.valid_until, *(format(v, ".2f") for v in [quote.total_ht, quote.tva, quote.total_ttc]), quote.get_status_display()]])
    return stream.getvalue().encode("utf-8-sig")
