from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .exchange_forms import (
    ExchangeCreateForm,
    ExchangeDocumentForm,
    ExchangeReplyForm,
)
from .exchange_services import (
    add_exchange_document,
    context_meta,
    create_exchange,
    mark_exchange_read,
    promote_exchange_document,
    reply_to_exchange,
    set_exchange_state,
    unread_exchange_queryset,
)
from .filters import filtered_exchanges
from .models import (
    AccountingDocument,
    AccountingExchange,
    AccountingExchangeDocument,
    AccountingExchangeMessage,
    AccountingExchangeReadState,
    SupplierInvoice,
)
from .services import complete_purchases, issued_invoices, shared_quotes
from .views import accounting_required, page_context


def _context_from_request(request):
    source = request.POST if request.method == "POST" else request.GET
    context_type = (source.get("context_type") or "").strip()
    context_id = (source.get("context_id") or "").strip()
    if not context_type and not context_id:
        return None, None, None
    if not context_type or not context_id or not context_id.isdigit():
        raise Http404("Contexte comptable introuvable.")

    pk = int(context_id)
    if context_type == "invoice":
        obj = get_object_or_404(issued_invoices(), pk=pk)
        field = "invoice"
    elif context_type == "quote":
        obj = get_object_or_404(shared_quotes(), pk=pk)
        field = "quote"
    elif context_type == "supplier_invoice":
        obj = get_object_or_404(
            complete_purchases(SupplierInvoice.objects.all()), pk=pk
        )
        field = "supplier_invoice"
    elif context_type == "accounting_document":
        obj = get_object_or_404(AccountingDocument.objects.all(), pk=pk)
        field = "accounting_document"
    else:
        raise Http404("Contexte comptable introuvable.")

    probe = AccountingExchange(subject="Contexte", **{field: obj})
    return field, obj, context_meta(probe)


def _visible_documents(request, exchange):
    documents = AccountingExchangeDocument.objects.filter(exchange=exchange).select_related(
        "uploaded_by", "promoted_to"
    )
    if not request.accounting_admin:
        documents = documents.filter(
            visibility=AccountingExchangeDocument.Visibility.SHARED
        )
    return documents


@accounting_required
def exchange_list(request):
    """List collaboration threads with role-aware métier filters."""
    queryset = AccountingExchange.objects.select_related(
        "created_by",
        "invoice__client",
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


@accounting_required
def exchange_create(request):
    context_field, context_object, context_information = _context_from_request(request)
    mode = (
        request.POST.get("mode") if request.method == "POST" else request.GET.get("mode")
    ) or "message"

    initial = {}
    if context_information:
        initial["subject"] = f"À propos de {context_information.reference}"[:200]
    if mode == "document":
        initial["kind"] = AccountingExchange.Kind.DOCUMENT_DELIVERY

    form = ExchangeCreateForm(
        request.POST or None,
        request.FILES or None,
        user=request.user,
        mode=mode,
        initial=initial if request.method != "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            exchange = create_exchange(
                request.user,
                subject=data["subject"],
                kind=data["kind"],
                priority=data["priority"],
                content=data.get("message", ""),
                file=data.get("file"),
                document_title=data.get("document_title", ""),
                document_type=data.get("document_type")
                or AccountingExchangeDocument.Type.OTHER,
                visibility=form.document_visibility(),
                context_field=context_field,
                context_object=context_object,
            )
        except IntegrityError:
            form.add_error("file", "Ce document est déjà présent dans cet échange.")
        else:
            messages.success(request, "Échange créé et transmis à l’autre partie.")
            return redirect("accounting:exchange_detail", pk=exchange.pk)

    return render(
        request,
        "accounting/exchange_form.html",
        page_context(
            request,
            form=form,
            mode=mode,
            context_type=context_field or "",
            context_id=getattr(context_object, "pk", ""),
            context_meta=context_information,
        ),
    )


@accounting_required
def exchange_detail(request, pk):
    exchange = get_object_or_404(
        AccountingExchange.objects.select_related(
            "created_by",
            "invoice__client",
            "quote__client",
            "supplier_invoice",
            "accounting_document",
        ),
        pk=pk,
    )
    mark_exchange_read(exchange, request.user)

    visible_documents = _visible_documents(request, exchange)
    message_queryset = AccountingExchangeMessage.objects.filter(exchange=exchange).select_related(
        "author"
    ).prefetch_related(
        Prefetch(
            "documents",
            queryset=visible_documents,
            to_attr="visible_documents",
        )
    )
    messages_list = list(message_queryset)
    standalone_documents = list(visible_documents.filter(message__isnull=True))
    all_documents = list(visible_documents)

    return render(
        request,
        "accounting/exchange_detail.html",
        page_context(
            request,
            exchange=exchange,
            context_meta=context_meta(exchange),
            exchange_messages=messages_list,
            standalone_documents=standalone_documents,
            exchange_documents=all_documents,
            reply_form=ExchangeReplyForm(user=request.user),
            document_form=ExchangeDocumentForm(user=request.user),
        ),
    )


@accounting_required
@require_POST
def exchange_reply(request, pk):
    exchange = get_object_or_404(AccountingExchange, pk=pk)
    form = ExchangeReplyForm(request.POST, request.FILES, user=request.user)
    if not form.is_valid():
        messages.error(
            request,
            "Réponse non envoyée. Vérifiez le message ou le document joint.",
        )
        return redirect("accounting:exchange_detail", pk=pk)

    data = form.cleaned_data
    try:
        reply_to_exchange(
            exchange,
            request.user,
            content=data.get("content", ""),
            file=data.get("file"),
            document_title=data.get("document_title", ""),
            document_type=data.get("document_type")
            or AccountingExchangeDocument.Type.OTHER,
            visibility=form.document_visibility(),
        )
    except IntegrityError:
        messages.error(request, "Ce document est déjà présent dans cet échange.")
    else:
        messages.success(request, "Réponse transmise.")
    return redirect("accounting:exchange_detail", pk=pk)


@accounting_required
@require_POST
def exchange_document_upload(request, pk):
    exchange = get_object_or_404(AccountingExchange, pk=pk)
    form = ExchangeDocumentForm(request.POST, request.FILES, user=request.user)
    if not form.is_valid():
        messages.error(request, "Document non publié. Vérifiez le fichier sélectionné.")
        return redirect("accounting:exchange_detail", pk=pk)

    data = form.cleaned_data
    try:
        add_exchange_document(
            exchange,
            request.user,
            file=data["file"],
            title=data["document_title"],
            document_type=data["document_type"],
            visibility=form.document_visibility(),
        )
    except IntegrityError:
        messages.error(request, "Ce document est déjà présent dans cet échange.")
    else:
        messages.success(request, "Document mis à disposition.")
    return redirect("accounting:exchange_detail", pk=pk)


@accounting_required
@require_POST
def exchange_status(request, pk):
    exchange = get_object_or_404(AccountingExchange, pk=pk)
    action = (request.POST.get("action") or "").strip()
    if action not in {"resolve", "reopen"}:
        return HttpResponseBadRequest("Action invalide.")
    set_exchange_state(exchange, request.user, action)
    messages.success(
        request,
        "Échange résolu." if action == "resolve" else "Échange rouvert.",
    )
    return redirect("accounting:exchange_detail", pk=pk)


@accounting_required
@require_POST
def exchange_document_promote(request, pk, document_id):
    if not request.accounting_admin:
        return HttpResponseForbidden("Action réservée à NetExpress.")
    exchange = get_object_or_404(AccountingExchange, pk=pk)
    document = get_object_or_404(
        AccountingExchangeDocument,
        pk=document_id,
        exchange=exchange,
    )
    target = promote_exchange_document(document, request.user)
    messages.success(
        request,
        f"« {target.title} » est maintenant classé dans les autres documents comptables.",
    )
    return redirect("accounting:exchange_detail", pk=pk)
