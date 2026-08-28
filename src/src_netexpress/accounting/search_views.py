from __future__ import annotations

from datetime import date

from django.db.models import Q
from django.shortcuts import render

from .exchange_services import context_meta
from .models import AccountingDocument, AccountingExchange, SupplierInvoice
from .services import complete_purchases, is_reviewed, issued_invoices
from .views import accounting_required, page_context

SEARCH_SCOPES = (
    ("all", "Tout l’espace"),
    ("sales", "Factures clients"),
    ("suppliers", "Factures fournisseurs"),
    ("documents", "Autres documents"),
    ("exchanges", "Échanges"),
)
SEARCH_LIMIT = 25


def _parse_date(raw: str | None):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _apply_date_range(queryset, field_name: str, date_from, date_to):
    if date_from:
        queryset = queryset.filter(**{f"{field_name}__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field_name}__lte": date_to})
    return queryset


def _apply_supplier_date_range(queryset, date_from, date_to):
    """Use creation date for supplier drafts that do not have an issue date yet."""
    if date_from:
        queryset = queryset.filter(
            Q(issue_date__gte=date_from)
            | Q(issue_date__isnull=True, created_at__date__gte=date_from)
        )
    if date_to:
        queryset = queryset.filter(
            Q(issue_date__lte=date_to)
            | Q(issue_date__isnull=True, created_at__date__lte=date_to)
        )
    return queryset


@accounting_required
def search(request):
    """Search every cabinet-visible accounting collection from one place."""
    query = (request.GET.get("q") or "").strip()[:100]
    scope = (request.GET.get("scope") or "all").strip()
    valid_scopes = {value for value, _ in SEARCH_SCOPES}
    if scope not in valid_scopes:
        scope = "all"

    raw_date_from = (request.GET.get("date_from") or "").strip()
    raw_date_to = (request.GET.get("date_to") or "").strip()
    date_from = _parse_date(raw_date_from)
    date_to = _parse_date(raw_date_to)
    filter_error = ""
    if raw_date_from and not date_from:
        filter_error = "La date de début est invalide."
    elif raw_date_to and not date_to:
        filter_error = "La date de fin est invalide."
    elif date_from and date_to and date_from > date_to:
        filter_error = "La date de début doit précéder la date de fin."

    result = {
        "sales": [],
        "suppliers": [],
        "documents": [],
        "exchanges": [],
    }
    counts = {key: 0 for key in result}

    if not filter_error:
        if scope in {"all", "sales"}:
            sales = issued_invoices()
            sales = _apply_date_range(sales, "issue_date", date_from, date_to)
            if query:
                sales = sales.filter(
                    Q(number__icontains=query)
                    | Q(quote__client__full_name__icontains=query)
                    | Q(quote__client__email__icontains=query)
                    | Q(invoice_items__description__icontains=query)
                ).distinct()
            counts["sales"] = sales.count()
            result["sales"] = list(sales[:SEARCH_LIMIT])
            for invoice in result["sales"]:
                invoice.accounting_checked = is_reviewed(invoice)

        if scope in {"all", "suppliers"}:
            suppliers = SupplierInvoice.objects.select_related("created_by")
            if not request.accounting_admin:
                suppliers = complete_purchases(suppliers)
            suppliers = _apply_supplier_date_range(suppliers, date_from, date_to)
            if query:
                suppliers = suppliers.filter(
                    Q(supplier_name__icontains=query)
                    | Q(reference__icontains=query)
                    | Q(notes__icontains=query)
                )
            counts["suppliers"] = suppliers.count()
            result["suppliers"] = list(suppliers[:SEARCH_LIMIT])

        if scope in {"all", "documents"}:
            documents = AccountingDocument.objects.select_related("created_by")
            documents = _apply_date_range(
                documents, "document_date", date_from, date_to
            )
            if query:
                documents = documents.filter(
                    Q(title__icontains=query)
                    | Q(notes__icontains=query)
                )
            counts["documents"] = documents.count()
            result["documents"] = list(documents[:SEARCH_LIMIT])

        if scope in {"all", "exchanges"}:
            exchanges = AccountingExchange.objects.select_related(
                "invoice__quote__client",
                "quote__client",
                "supplier_invoice",
                "accounting_document",
                "created_by",
            )
            if date_from:
                exchanges = exchanges.filter(last_activity_at__date__gte=date_from)
            if date_to:
                exchanges = exchanges.filter(last_activity_at__date__lte=date_to)
            if query:
                exchanges = exchanges.filter(
                    Q(subject__icontains=query)
                    | Q(messages__content__icontains=query)
                    | Q(invoice__number__icontains=query)
                    | Q(invoice__quote__client__full_name__icontains=query)
                    | Q(quote__number__icontains=query)
                    | Q(quote__client__full_name__icontains=query)
                    | Q(supplier_invoice__supplier_name__icontains=query)
                    | Q(supplier_invoice__reference__icontains=query)
                    | Q(accounting_document__title__icontains=query)
                ).distinct()
            counts["exchanges"] = exchanges.count()
            result["exchanges"] = list(exchanges[:SEARCH_LIMIT])
            for exchange in result["exchanges"]:
                exchange.search_context = context_meta(exchange)

    total_count = sum(counts.values())
    return render(
        request,
        "accounting/search.html",
        page_context(
            request,
            query=query,
            scope=scope,
            scopes=SEARCH_SCOPES,
            raw_date_from=raw_date_from,
            raw_date_to=raw_date_to,
            filter_error=filter_error,
            result=result,
            counts=counts,
            total_count=total_count,
            result_limit=SEARCH_LIMIT,
            filters_active=bool(query or raw_date_from or raw_date_to or scope != "all"),
        ),
    )
