"""Workflow-oriented views for the accounting portal.

These views deliberately stay separate from the CRUD views in ``views.py``:
the goal is to improve the day-to-day workspace without changing the accounting
models or the existing permissions.
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
from .forms import ReviewForm
from .models import AccountingActivity, AccountingDocument, InvoiceReview, SupplierInvoice
from .services import (
    incomplete_purchases,
    invoice_fingerprint,
    is_reviewed,
    log_activity,
    period_quotes,
    supporting_documents,
)
from .views import accounting_required, filtered, page_context

RETURN_QUERY_KEYS = {"date_from", "date_to", "q", "pending", "incomplete", "kind", "page"}


def _share(count, total):
    """Return a rounded percentage for visual workload indicators."""
    if not total:
        return 0
    return round((count / total) * 100)


def _reviewable_purchases(purchases):
    """Purchases the cabinet can actually process right now."""
    incomplete_ids = incomplete_purchases(purchases).values("pk")
    return purchases.filter(reviewed_at__isnull=True).exclude(pk__in=incomplete_ids)


def _safe_return_query(raw):
    """Keep only accounting list filters when returning from a detail review."""
    if not raw:
        return ""
    pairs = [(key, value) for key, value in parse_qsl(raw, keep_blank_values=False) if key in RETURN_QUERY_KEYS]
    return urlencode(pairs)


def _redirect_detail(route_name, pk, request):
    query = _safe_return_query(request.POST.get("return_query", ""))
    url = reverse(route_name, kwargs={"pk": pk})
    return redirect(f"{url}?{query}" if query else url)


@accounting_required
def dashboard(request):
    form, sales, purchases = filtered(request)
    documents = supporting_documents(form.cleaned_data) if form.is_valid() else AccountingDocument.objects.none()
    quotes = period_quotes(form.cleaned_data) if form.is_valid() else period_quotes({
        "date_from": timezone.localdate(),
        "date_to": timezone.localdate(),
        "q": "",
    }).none()

    totals = {
        "sales": Decimal(0),
        "credits": Decimal(0),
        "sales_vat": Decimal(0),
        "pending_sales": 0,
    }
    for invoice in sales.iterator(chunk_size=200):
        totals["credits" if invoice.is_credit_note else "sales"] += invoice.total_ttc
        totals["sales_vat"] += invoice.tva * (-1 if invoice.is_credit_note else 1)
        totals["pending_sales"] += not is_reviewed(invoice)

    totals["net_sales"] = totals["sales"] - totals["credits"]
    totals["purchases"] = purchases.aggregate(total=Sum("total_ttc"))["total"] or Decimal(0)
    totals["incomplete_purchases"] = incomplete_purchases(purchases).count()
    totals["pending_purchases"] = _reviewable_purchases(purchases).count()
    totals["documents"] = documents.count()
    totals["quotes"] = quotes.count()
    totals["pending_documents"] = documents.filter(reviewed_at__isnull=True).count()
    totals["pending"] = totals["pending_sales"] + totals["pending_purchases"] + totals["pending_documents"]
    totals["unresolved"] = totals["pending"] + totals["incomplete_purchases"]
    totals["count"] = sales.count() + purchases.count() + totals["documents"]
    totals["reviewed"] = max(totals["count"] - totals["unresolved"], 0)
    totals["progress"] = round((totals["reviewed"] / totals["count"]) * 100) if totals["count"] else 0
    totals["overdue_purchases"] = purchases.filter(
        paid_on__isnull=True,
        due_date__lt=timezone.localdate(),
    ).count()

    workload = [
        {
            "label": "Factures clients",
            "count": totals["pending_sales"],
            "share": _share(totals["pending_sales"], totals["pending"]),
        },
        {
            "label": "Factures fournisseurs prêtes",
            "count": totals["pending_purchases"],
            "share": _share(totals["pending_purchases"], totals["pending"]),
        },
        {
            "label": "Autres documents",
            "count": totals["pending_documents"],
            "share": _share(totals["pending_documents"], totals["pending"]),
        },
    ]

    activities = AccountingActivity.objects.select_related("actor")
    if not request.accounting_admin:
        activities = activities.exclude(action__startswith="Accès cabinet").exclude(
            action__startswith="Invitation cabinet"
        )

    return render(
        request,
        "accounting/dashboard.html",
        page_context(
            request,
            form=form,
            totals=totals,
            workload=workload,
            recent_sales=sales[:5],
            recent_purchases=purchases[:5],
            recent_documents=documents[:4],
            recent_quotes=quotes[:4],
            activities=activities[:8],
        ),
    )


@accounting_required
def sales(request):
    """Invoice list with a real review queue for the external accountant."""
    form, invoices, _ = filtered(request)
    pending_only = request.GET.get("pending") == "1"

    if pending_only:
        # A stored review can become stale when an issued invoice changes. The
        # fingerprint check is therefore intentionally kept instead of relying
        # only on ``accounting_review__isnull``.
        invoices = [invoice for invoice in invoices if not is_reviewed(invoice)]

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
            pending_only=pending_only,
        ),
    )


@accounting_required
def suppliers(request):
    """Purchase list with mutually exclusive 'reviewable' and 'incomplete' queues."""
    form, _, purchases = filtered(request)
    pending_only = request.GET.get("pending") == "1"
    incomplete_only = request.GET.get("incomplete") == "1"

    if incomplete_only:
        purchases = incomplete_purchases(purchases)
    elif pending_only:
        purchases = _reviewable_purchases(purchases)

    total = purchases.aggregate(total=Sum("total_ttc"))["total"] or Decimal(0)
    incomplete_count = incomplete_purchases(purchases).count()

    return render(
        request,
        "accounting/suppliers.html",
        page_context(
            request,
            form=form,
            total=total,
            incomplete_count=incomplete_count,
            pending_only=pending_only,
            incomplete_only=incomplete_only,
            page=Paginator(purchases.select_related("created_by"), 40).get_page(request.GET.get("page")),
        ),
    )


@accounting_required
@require_POST
@transaction.atomic
def review_invoice(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")
    invoice = get_object_or_404(Invoice.all_objects.select_for_update(), pk=pk, issued_at__isnull=False)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    fingerprint = invoice_fingerprint(invoice)
    if form.cleaned_data["fingerprint"] != fingerprint:
        messages.error(request, "La facture a changé depuis l’ouverture. Relisez-la avant de la contrôler.")
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
        messages.success(request, "Facture marquée comme contrôlée dans le portail.")
    return _redirect_detail("accounting:invoice_detail", pk, request)


@accounting_required
@require_POST
@transaction.atomic
def review_supplier(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")
    purchase = get_object_or_404(SupplierInvoice.objects.select_for_update(), pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    if not purchase.is_complete:
        messages.error(request, "Complétez le fournisseur, le numéro, la date, le TTC et la TVA avant le contrôle.")
    elif form.cleaned_data["fingerprint"] != purchase.updated_at.isoformat():
        messages.error(request, "La facture a changé. Relisez-la avant de la contrôler.")
    else:
        purchase.reviewed_at = timezone.now()
        purchase.reviewed_by = request.user
        purchase.review_note = form.cleaned_data["note"]
        purchase.save(update_fields=["reviewed_at", "reviewed_by", "review_note", "updated_at"])
        log_activity(request.user, "Facture fournisseur contrôlée", purchase)
        messages.success(request, "Facture marquée comme contrôlée dans le portail.")
    return _redirect_detail("accounting:supplier_detail", pk, request)


@accounting_required
@require_POST
@transaction.atomic
def review_document(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")
    document = get_object_or_404(AccountingDocument.objects.select_for_update(), pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    if form.cleaned_data["fingerprint"] != document.updated_at.isoformat():
        messages.error(request, "Le document a changé. Relisez-le avant de le vérifier.")
    else:
        document.reviewed_at = timezone.now()
        document.reviewed_by = request.user
        document.review_note = form.cleaned_data["note"]
        document.save(update_fields=["reviewed_at", "reviewed_by", "review_note", "updated_at"])
        log_activity(request.user, "Document vérifié", document)
        messages.success(request, "Document marqué comme vérifié dans le portail.")
    return _redirect_detail("accounting:document_detail", pk, request)
