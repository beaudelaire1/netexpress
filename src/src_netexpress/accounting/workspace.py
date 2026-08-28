"""Workflow-oriented views for the accounting portal.

The accounting workspace only presents pieces that the cabinet can act on.
Operational drafts remain in the NetExpress preparation flow and are never
mixed with the accountant's review queue or financial indicators.
"""
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from factures.models import Invoice
from .filters import filtered_sales, filtered_suppliers
from .forms import ReviewForm
from .models import AccountingActivity, AccountingDocument, InvoiceReview, SupplierInvoice
from .services import (
    complete_purchases,
    incomplete_purchases,
    invoice_fingerprint,
    is_reviewed,
    issued_invoices,
    log_activity,
    supporting_documents,
)
from .views import accounting_required, filtered, page_context

RETURN_QUERY_KEYS = {
    "date_from",
    "date_to",
    "q",
    "status",
    "review",
    "document_type",
    "category",
    "payment",
    "completeness",
    "amount_min",
    "amount_max",
    "exchange",
    "kind",
    "source",
    "priority",
    "documents",
    "unread",
    "context",
    "page",
}

MONTHS_FR = (
    "Janv.",
    "Févr.",
    "Mars",
    "Avr.",
    "Mai",
    "Juin",
    "Juil.",
    "Août",
    "Sept.",
    "Oct.",
    "Nov.",
    "Déc.",
)


def _share(count, total):
    if not total:
        return 0
    return round((count / total) * 100)


def _safe_return_query(raw):
    if not raw:
        return ""
    pairs = [
        (key, value)
        for key, value in parse_qsl(raw, keep_blank_values=False)
        if key in RETURN_QUERY_KEYS
    ]
    return urlencode(pairs)


def _redirect_detail(route_name, pk, request):
    query = _safe_return_query(request.POST.get("return_query", ""))
    url = reverse(route_name, kwargs={"pk": pk})
    return redirect(f"{url}?{query}" if query else url)


def _financial_series(sales, purchases, date_from, date_to):
    """Build chart-ready monthly data, switching to annual buckets for long ranges."""
    month_span = (date_to.year - date_from.year) * 12 + date_to.month - date_from.month + 1
    annual = month_span > 24
    buckets = {}

    if annual:
        for year in range(date_from.year, date_to.year + 1):
            buckets[year] = {
                "label": str(year),
                "sales": Decimal("0.00"),
                "purchases": Decimal("0.00"),
                "sales_vat": Decimal("0.00"),
                "purchase_vat": Decimal("0.00"),
            }
    else:
        year, month = date_from.year, date_from.month
        while (year, month) <= (date_to.year, date_to.month):
            key = (year, month)
            buckets[key] = {
                "label": f"{MONTHS_FR[month - 1]} {year}",
                "sales": Decimal("0.00"),
                "purchases": Decimal("0.00"),
                "sales_vat": Decimal("0.00"),
                "purchase_vat": Decimal("0.00"),
            }
            month += 1
            if month == 13:
                month = 1
                year += 1

    for invoice in sales:
        key = invoice.issue_date.year if annual else (invoice.issue_date.year, invoice.issue_date.month)
        if key not in buckets:
            continue
        sign = Decimal("-1") if invoice.is_credit_note else Decimal("1")
        buckets[key]["sales"] += sign * invoice.total_ht
        buckets[key]["sales_vat"] += sign * invoice.tva

    for purchase in purchases:
        if not purchase.issue_date:
            continue
        key = purchase.issue_date.year if annual else (purchase.issue_date.year, purchase.issue_date.month)
        if key not in buckets:
            continue
        buckets[key]["purchases"] += purchase.total_ht or Decimal("0.00")
        buckets[key]["purchase_vat"] += purchase.vat_amount or Decimal("0.00")

    return [
        {
            "label": row["label"],
            "sales": float(row["sales"]),
            "purchases": float(row["purchases"]),
            "sales_vat": float(row["sales_vat"]),
            "purchase_vat": float(row["purchase_vat"]),
        }
        for row in buckets.values()
    ]


@accounting_required
def dashboard(request):
    form, sales_qs, purchases_qs = filtered(request)
    documents = (
        supporting_documents(form.cleaned_data)
        if form.is_valid()
        else AccountingDocument.objects.none()
    )

    if not form.is_valid():
        return render(
            request,
            "accounting/dashboard.html",
            page_context(
                request,
                form=form,
                totals={},
                workload=[],
                financial_series=[],
                recent_sales=[],
                recent_purchases=[],
                recent_documents=[],
                activities=[],
            ),
        )

    # Les indicateurs financiers ne mélangent jamais les dépôts fournisseurs
    # encore en préparation, même quand un administrateur NetExpress consulte
    # le même espace que le cabinet.
    ready_purchases_qs = complete_purchases(purchases_qs)
    sales = list(sales_qs)
    ready_purchases = list(ready_purchases_qs)

    totals = {
        "sales_ttc": Decimal("0.00"),
        "credits_ttc": Decimal("0.00"),
        "sales_ht": Decimal("0.00"),
        "credits_ht": Decimal("0.00"),
        "sales_vat": Decimal("0.00"),
        "purchases_ttc": Decimal("0.00"),
        "purchases_ht": Decimal("0.00"),
        "purchase_vat": Decimal("0.00"),
        "pending_sales": 0,
        "pending_purchases": 0,
    }

    for invoice in sales:
        if invoice.is_credit_note:
            totals["credits_ttc"] += invoice.total_ttc
            totals["credits_ht"] += invoice.total_ht
            totals["sales_vat"] -= invoice.tva
        else:
            totals["sales_ttc"] += invoice.total_ttc
            totals["sales_ht"] += invoice.total_ht
            totals["sales_vat"] += invoice.tva
        totals["pending_sales"] += int(not is_reviewed(invoice))

    for purchase in ready_purchases:
        totals["purchases_ttc"] += purchase.total_ttc or Decimal("0.00")
        totals["purchases_ht"] += purchase.total_ht or Decimal("0.00")
        totals["purchase_vat"] += purchase.vat_amount or Decimal("0.00")
        totals["pending_purchases"] += int(purchase.reviewed_at is None)

    totals["net_sales"] = totals["sales_ttc"] - totals["credits_ttc"]
    totals["net_sales_ht"] = totals["sales_ht"] - totals["credits_ht"]
    totals["purchases"] = totals["purchases_ttc"]
    totals["credits"] = totals["credits_ttc"]

    totals["incomplete_purchases"] = (
        incomplete_purchases(purchases_qs).count() if request.accounting_admin else 0
    )
    totals["documents"] = documents.count()
    totals["pending_documents"] = documents.filter(reviewed_at__isnull=True).count()
    totals["pending"] = (
        totals["pending_sales"]
        + totals["pending_purchases"]
        + totals["pending_documents"]
    )
    totals["count"] = len(sales) + len(ready_purchases) + totals["documents"]
    totals["reviewed"] = max(totals["count"] - totals["pending"], 0)
    totals["progress"] = (
        round((totals["reviewed"] / totals["count"]) * 100)
        if totals["count"]
        else 0
    )
    totals["overdue_purchases"] = sum(
        1 for purchase in ready_purchases if purchase.is_overdue
    )

    workload = [
        {
            "label": "Factures clients",
            "count": totals["pending_sales"],
            "share": _share(totals["pending_sales"], totals["pending"]),
        },
        {
            "label": "Factures fournisseurs",
            "count": totals["pending_purchases"],
            "share": _share(totals["pending_purchases"], totals["pending"]),
        },
        {
            "label": "Autres documents",
            "count": totals["pending_documents"],
            "share": _share(totals["pending_documents"], totals["pending"]),
        },
    ]

    financial_series = _financial_series(
        sales,
        ready_purchases,
        form.cleaned_data["date_from"],
        form.cleaned_data["date_to"],
    )

    activities = AccountingActivity.objects.select_related("actor")
    if not request.accounting_admin:
        activities = activities.exclude(action__startswith="Accès cabinet").exclude(
            action__startswith="Invitation cabinet"
        )

    # Un administrateur peut reprendre rapidement un dépôt récent à compléter ;
    # le cabinet ne reçoit, lui, que des factures fournisseurs complètes.
    recent_purchase_source = (
        list(purchases_qs[:5]) if request.accounting_admin else ready_purchases[:5]
    )

    return render(
        request,
        "accounting/dashboard.html",
        page_context(
            request,
            form=form,
            totals=totals,
            workload=workload,
            financial_series=financial_series,
            recent_sales=sales[:5],
            recent_purchases=recent_purchase_source,
            recent_documents=documents[:4],
            activities=activities[:8],
        ),
    )


@accounting_required
def sales(request):
    """Client invoices with accountant-oriented search and filters."""
    form, invoices = filtered_sales(request)
    page = Paginator(invoices, 40).get_page(request.GET.get("page"))
    for invoice in page:
        invoice.accounting_checked = is_reviewed(invoice)

    return render(
        request,
        "accounting/sales.html",
        page_context(
            request,
            form=form,
            page=page,
            result_count=page.paginator.count,
            filter_kind="sales",
            active_filters=form.active_filter_chips(request),
            advanced_filter_count=form.active_advanced_count(request),
        ),
    )


@accounting_required
def suppliers(request):
    """Supplier queue with role-aware preparation, payment and review filters."""
    form, purchases = filtered_suppliers(request)
    total = purchases.aggregate(total=Sum("total_ttc"))["total"] or Decimal("0.00")
    page = Paginator(
        purchases.select_related("created_by"), 40
    ).get_page(request.GET.get("page"))

    return render(
        request,
        "accounting/suppliers.html",
        page_context(
            request,
            form=form,
            total=total,
            result_count=page.paginator.count,
            filter_kind="suppliers",
            active_filters=form.active_filter_chips(request),
            advanced_filter_count=form.active_advanced_count(request),
            page=page,
        ),
    )


@accounting_required
@require_POST
@transaction.atomic
def review_invoice(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")

    if not issued_invoices().filter(pk=pk).exists():
        return HttpResponseForbidden("Cette facture n’est pas disponible au contrôle comptable.")
    invoice = get_object_or_404(Invoice.all_objects.select_for_update(), pk=pk)

    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    fingerprint = invoice_fingerprint(invoice)
    if form.cleaned_data["fingerprint"] != fingerprint:
        messages.error(
            request,
            "La facture a changé depuis l’ouverture. Relisez-la avant de la contrôler.",
        )
    else:
        InvoiceReview.objects.update_or_create(
            invoice=invoice,
            defaults={
                "fingerprint": fingerprint,
                "note": form.cleaned_data["note"],
                "reviewed_by": request.user,
                "reviewed_at": timezone.now(),
            },
        )
        log_activity(request.user, "Facture client contrôlée", invoice.number)
        messages.success(
            request,
            "Facture marquée comme contrôlée dans le portail.",
        )
    return _redirect_detail("accounting:invoice_detail", pk, request)


@accounting_required
@require_POST
@transaction.atomic
def review_supplier(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")

    complete = complete_purchases(SupplierInvoice.objects.select_for_update())
    purchase = get_object_or_404(complete, pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    if form.cleaned_data["fingerprint"] != purchase.updated_at.isoformat():
        messages.error(
            request,
            "La facture a changé. Relisez-la avant de la contrôler.",
        )
    else:
        purchase.reviewed_at = timezone.now()
        purchase.reviewed_by = request.user
        purchase.review_note = form.cleaned_data["note"]
        purchase.save(
            update_fields=[
                "reviewed_at",
                "reviewed_by",
                "review_note",
                "updated_at",
            ]
        )
        log_activity(request.user, "Facture fournisseur contrôlée", purchase)
        messages.success(
            request,
            "Facture marquée comme contrôlée dans le portail.",
        )
    return _redirect_detail("accounting:supplier_detail", pk, request)


@accounting_required
@require_POST
@transaction.atomic
def review_document(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")
    document = get_object_or_404(
        AccountingDocument.objects.select_for_update(), pk=pk
    )
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    if form.cleaned_data["fingerprint"] != document.updated_at.isoformat():
        messages.error(
            request,
            "Le document a changé. Relisez-le avant de le vérifier.",
        )
    else:
        document.reviewed_at = timezone.now()
        document.reviewed_by = request.user
        document.review_note = form.cleaned_data["note"]
        document.save(
            update_fields=[
                "reviewed_at",
                "reviewed_by",
                "review_note",
                "updated_at",
            ]
        )
        log_activity(request.user, "Document vérifié", document)
        messages.success(request, "Document marqué comme vérifié dans le portail.")
    return _redirect_detail("accounting:document_detail", pk, request)
