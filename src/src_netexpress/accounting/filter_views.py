from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import render

from .exchange_services import context_meta, unread_exchange_queryset
from .filters import filtered_documents, filtered_exchanges
from .models import (
    AccountingExchange,
    AccountingExchangeDocument,
    AccountingExchangeReadState,
)
from .views import accounting_required, page_context


@accounting_required
def documents(request):
    form, pieces = filtered_documents(request)
    page = Paginator(
        pieces.select_related("created_by"), 40
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "accounting/documents.html",
        page_context(
            request,
            form=form,
            page=page,
            result_count=page.paginator.count,
            filter_kind="documents",
            active_filters=form.active_filter_chips(request),
            advanced_filter_count=form.active_advanced_count(request),
        ),
    )


@accounting_required
def exchanges(request):
    queryset = AccountingExchange.objects.select_related(
        "created_by",
        "invoice__quote__client",
        "quote__client",
        "supplier_invoice",
        "accounting_document",
    )
    form, queryset = filtered_exchanges(request, queryset)
    if form.is_valid() and form.cleaned_data.get("unread"):
        queryset = unread_exchange_queryset(request.user, queryset)

    read_state = AccountingExchangeReadState.objects.filter(
        exchange_id=OuterRef("pk"),
        user=request.user,
        last_read_at__gte=OuterRef("last_activity_at"),
    )
    document_filter = Q()
    if not request.accounting_admin:
        document_filter = Q(
            documents__visibility=AccountingExchangeDocument.Visibility.SHARED
        )

    queryset = queryset.annotate(
        is_read=Exists(read_state),
        document_count=Count("documents", filter=document_filter, distinct=True),
        message_count=Count("messages", distinct=True),
    )
    page = Paginator(queryset, 30).get_page(request.GET.get("page"))
    for exchange in page.object_list:
        exchange.context_meta = context_meta(exchange)

    return render(
        request,
        "accounting/exchanges.html",
        page_context(
            request,
            form=form,
            page=page,
            result_count=page.paginator.count,
            filter_kind="exchanges",
            active_filters=form.active_filter_chips(request),
            advanced_filter_count=form.active_advanced_count(request),
        ),
    )
