"""Workflow-oriented views for the accounting portal.

These views deliberately stay separate from the CRUD/review views in ``views.py``:
the goal is to improve the day-to-day workspace without changing the accounting
models or the existing review responsibilities.
"""
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .models import AccountingActivity, AccountingDocument, SupplierInvoice
from .services import (
    incomplete_purchases,
    is_reviewed,
    period_quotes,
    supporting_documents,
)
from .views import accounting_required, filtered, page_context


def _share(count, total):
    """Return a rounded percentage for visual workload indicators."""
    if not total:
        return 0
    return round((count / total) * 100)


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
    totals["pending_purchases"] = purchases.filter(reviewed_at__isnull=True).count()
    totals["incomplete_purchases"] = incomplete_purchases(purchases).count()
    totals["documents"] = documents.count()
    totals["quotes"] = quotes.count()
    totals["pending_documents"] = documents.filter(reviewed_at__isnull=True).count()
    totals["pending"] = totals["pending_sales"] + totals["pending_purchases"] + totals["pending_documents"]
    totals["count"] = sales.count() + purchases.count() + totals["documents"]
    totals["reviewed"] = max(totals["count"] - totals["pending"], 0)
    totals["progress"] = round((totals["reviewed"] / totals["count"]) * 100) if totals["count"] else 100
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
