import csv
import hashlib
import io
import json
from decimal import Decimal

from django.db.models import Q
from factures.models import Invoice
from .models import SupplierInvoice, AccountingActivity


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


def period_documents(data):
    sales = issued_invoices().filter(issue_date__range=(data["date_from"], data["date_to"]))
    purchases = SupplierInvoice.objects.filter(issue_date__range=(data["date_from"], data["date_to"]))
    query = data.get("q", "")
    if query:
        sales = sales.filter(Q(number__icontains=query) | Q(quote__client__full_name__icontains=query))
        purchases = purchases.filter(Q(supplier_name__icontains=query) | Q(reference__icontains=query))
    return sales, purchases


def csv_cell(value):
    text = str(value if value is not None else "")
    # Prevent spreadsheet formulas, including leading whitespace before =, +, -, @.
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def csv_content(sales, purchases):
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
            purchase.due_date, format(purchase.total_ht, ".2f"), format(purchase.vat_amount, ".2f"), format(purchase.total_ttc, ".2f"),
            purchase.paid_on or "Non payé", "Comptabilisé" if purchase.reviewed_at else "À vérifier", purchase.notes]])
    return stream.getvalue().encode("utf-8-sig")
