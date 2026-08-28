from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from accounts.portal import get_user_role
from core.services.notification_service import notification_service

from .models import (
    AccountingDocument,
    AccountingExchange,
    AccountingExchangeDocument,
    AccountingExchangeMessage,
    AccountingExchangeReadState,
)
from .services import log_activity


@dataclass(frozen=True)
class ExchangeContext:
    kind: str
    label: str
    reference: str
    detail: str
    url: str
    amount: str = ""


def context_meta(exchange: AccountingExchange) -> ExchangeContext | None:
    if exchange.invoice_id:
        invoice = exchange.invoice
        client = getattr(getattr(invoice, "quote", None), "client", None)
        return ExchangeContext(
            kind="Facture client",
            label=invoice.number,
            reference=invoice.number,
            detail=getattr(client, "full_name", "") or "Client",
            url=reverse("accounting:invoice_detail", args=[invoice.pk]),
            amount=f"{invoice.total_ttc:.2f} €",
        )
    if exchange.quote_id:
        quote = exchange.quote
        return ExchangeContext(
            kind="Devis lié",
            label=quote.number,
            reference=quote.number,
            detail=getattr(quote.client, "full_name", "") or "Client",
            url=reverse("accounting:quote_detail", args=[quote.pk]),
            amount=f"{quote.total_ttc:.2f} €",
        )
    if exchange.supplier_invoice_id:
        purchase = exchange.supplier_invoice
        reference = purchase.reference or "Référence à compléter"
        return ExchangeContext(
            kind="Facture fournisseur",
            label=purchase.display_name,
            reference=reference,
            detail=reference,
            url=reverse("accounting:supplier_detail", args=[purchase.pk]),
            amount=(f"{purchase.total_ttc:.2f} €" if purchase.total_ttc is not None else ""),
        )
    if exchange.accounting_document_id:
        document = exchange.accounting_document
        return ExchangeContext(
            kind=document.get_kind_display(),
            label=document.title,
            reference=document.title,
            detail=document.document_date.strftime("%d/%m/%Y"),
            url=reverse("accounting:document_detail", args=[document.pk]),
        )
    return None


def waiting_status_for_actor(user) -> str:
    role = get_user_role(user)
    if role == Profile.ROLE_ACCOUNTANT:
        return AccountingExchange.Status.WAITING_NETEXPRESS
    return AccountingExchange.Status.WAITING_ACCOUNTANT


def mark_exchange_read(exchange: AccountingExchange, user) -> None:
    AccountingExchangeReadState.objects.update_or_create(
        exchange=exchange,
        user=user,
        defaults={"last_read_at": timezone.now()},
    )


def unread_exchange_queryset(user, queryset=None):
    queryset = queryset if queryset is not None else AccountingExchange.objects.all()
    read_state = AccountingExchangeReadState.objects.filter(
        exchange_id=OuterRef("pk"),
        user=user,
        last_read_at__gte=OuterRef("last_activity_at"),
    )
    return queryset.annotate(_is_read=Exists(read_state)).filter(_is_read=False)


def unread_exchange_count(user) -> int:
    if not getattr(user, "is_authenticated", False):
        return 0
    return unread_exchange_queryset(user).count()


def _counterparty_users(actor):
    User = get_user_model()
    role = get_user_role(actor)
    users = User.objects.filter(is_active=True).select_related("profile")
    if role == Profile.ROLE_ACCOUNTANT:
        return list(
            users.filter(
                profile__role__in=[
                    Profile.ROLE_ADMIN_BUSINESS,
                    Profile.ROLE_ADMIN_TECHNICAL,
                ]
            ).exclude(pk=actor.pk)
        )

    candidates = users.filter(profile__role=Profile.ROLE_ACCOUNTANT).exclude(pk=actor.pk)
    return [user for user in candidates if user.profile.has_verified_email]


def _notify_counterparty(exchange: AccountingExchange, actor, event: str) -> None:
    recipients = _counterparty_users(actor)
    if not recipients:
        return

    path = reverse("accounting:exchange_detail", args=[exchange.pk])
    actor_name = actor.get_full_name() or actor.username
    meta = context_meta(exchange)
    context_label = f" · {meta.reference}" if meta else ""
    title = f"Échange comptable : {exchange.subject}"
    message = f"{actor_name} — {event}{context_label}"

    for recipient in recipients:
        notification_service.create_ui_notification(
            user=recipient,
            title=title,
            message=message,
            notification_type="accounting_exchange",
            link_url=path,
        )
        if recipient.email:
            notification_service.send_email_notification(
                to_emails=[recipient.email],
                subject=title,
                template_name="accounting_exchange_notification",
                context={
                    "exchange": exchange,
                    "recipient": recipient,
                    "actor": actor,
                    "event": event,
                    "context_meta": meta,
                    "exchange_url": notification_service._build_portal_link(path),
                    "company_name": "NetExpress",
                },
            )


def queue_exchange_notification(exchange, actor, event: str) -> None:
    transaction.on_commit(lambda: _notify_counterparty(exchange, actor, event))


def _build_document(exchange, actor, *, file, title, document_type, visibility, message=None):
    document = AccountingExchangeDocument(
        exchange=exchange,
        message=message,
        uploaded_by=actor,
        title=title,
        document_type=document_type or AccountingExchangeDocument.Type.OTHER,
        visibility=visibility or AccountingExchangeDocument.Visibility.SHARED,
        file=file,
    )
    document.full_clean()
    document.save()
    return document


@transaction.atomic
def create_exchange(
    actor,
    *,
    subject: str,
    kind: str,
    priority: str,
    content: str = "",
    file=None,
    document_title: str = "",
    document_type: str = AccountingExchangeDocument.Type.OTHER,
    visibility: str = AccountingExchangeDocument.Visibility.SHARED,
    context_field: str | None = None,
    context_object: Any = None,
) -> AccountingExchange:
    exchange = AccountingExchange(
        subject=subject,
        kind=kind,
        priority=priority,
        status=waiting_status_for_actor(actor),
        created_by=actor,
    )
    if context_field and context_object is not None:
        setattr(exchange, context_field, context_object)
    exchange.full_clean()
    exchange.save()

    message = None
    if content:
        message = AccountingExchangeMessage(
            exchange=exchange,
            author=actor,
            content=content,
        )
        message.full_clean()
        message.save()

    if file:
        _build_document(
            exchange,
            actor,
            file=file,
            title=document_title,
            document_type=document_type,
            visibility=visibility,
            message=message,
        )

    mark_exchange_read(exchange, actor)
    log_activity(actor, "Échange comptable créé", exchange.subject)
    queue_exchange_notification(exchange, actor, "nouvel échange")
    return exchange


@transaction.atomic
def reply_to_exchange(
    exchange: AccountingExchange,
    actor,
    *,
    content: str = "",
    file=None,
    document_title: str = "",
    document_type: str = AccountingExchangeDocument.Type.OTHER,
    visibility: str = AccountingExchangeDocument.Visibility.SHARED,
):
    message = None
    if content:
        message = AccountingExchangeMessage(
            exchange=exchange,
            author=actor,
            content=content,
        )
        message.full_clean()
        message.save()

    document = None
    if file:
        document = _build_document(
            exchange,
            actor,
            file=file,
            title=document_title,
            document_type=document_type,
            visibility=visibility,
            message=message,
        )

    exchange.status = waiting_status_for_actor(actor)
    exchange.last_activity_at = timezone.now()
    exchange.save(update_fields=["status", "last_activity_at", "updated_at"])
    mark_exchange_read(exchange, actor)
    log_activity(actor, "Échange comptable mis à jour", exchange.subject)
    queue_exchange_notification(
        exchange,
        actor,
        "nouveau message" if content else "nouveau document",
    )
    return message, document


@transaction.atomic
def add_exchange_document(
    exchange: AccountingExchange,
    actor,
    *,
    file,
    title: str,
    document_type: str,
    visibility: str,
):
    document = _build_document(
        exchange,
        actor,
        file=file,
        title=title,
        document_type=document_type,
        visibility=visibility,
    )
    exchange.status = waiting_status_for_actor(actor)
    exchange.last_activity_at = timezone.now()
    exchange.save(update_fields=["status", "last_activity_at", "updated_at"])
    mark_exchange_read(exchange, actor)
    log_activity(actor, "Document partagé dans un échange", document.title)
    queue_exchange_notification(exchange, actor, f"document partagé : {document.title}")
    return document


@transaction.atomic
def set_exchange_state(exchange: AccountingExchange, actor, action: str) -> None:
    if action == "resolve":
        exchange.status = AccountingExchange.Status.RESOLVED
        event = "échange marqué comme résolu"
    elif action == "reopen":
        exchange.status = waiting_status_for_actor(actor)
        event = "échange rouvert"
    else:
        raise ValueError("Action de statut invalide")

    exchange.last_activity_at = timezone.now()
    exchange.save(update_fields=["status", "last_activity_at", "updated_at"])
    mark_exchange_read(exchange, actor)
    log_activity(actor, "Statut d’échange modifié", f"{exchange.subject} — {exchange.get_status_display()}")
    queue_exchange_notification(exchange, actor, event)


@transaction.atomic
def promote_exchange_document(document: AccountingExchangeDocument, actor) -> AccountingDocument:
    if document.promoted_to_id:
        return document.promoted_to

    target = None
    if document.file_sha256:
        target = AccountingDocument.objects.filter(file_sha256=document.file_sha256).first()

    if target is None:
        uploader = document.uploaded_by
        uploader_name = (
            (uploader.get_full_name() or uploader.username)
            if uploader
            else "Compte supprimé"
        )
        note = (
            f"Document reçu via l’échange « {document.exchange.subject} ». "
            f"Transmis par {uploader_name}."
        )
        candidate = AccountingDocument(
            title=document.title,
            kind=AccountingDocument.Kind.OTHER,
            document_date=timezone.localdate(),
            notes=note[:4000],
            file=document.file.name,
            file_sha256=document.file_sha256,
            created_by=actor,
        )
        candidate.full_clean(exclude=["file"])
        try:
            with transaction.atomic():
                candidate.save()
            target = candidate
        except IntegrityError:
            target = AccountingDocument.objects.get(file_sha256=document.file_sha256)

    document.promoted_to = target
    document.save(update_fields=["promoted_to"])
    log_activity(actor, "Document reçu ajouté au dossier comptable", target.title)
    return target


def exchange_search_query(queryset, term: str):
    term = (term or "").strip()
    if not term:
        return queryset
    return queryset.filter(
        Q(subject__icontains=term)
        | Q(invoice__number__icontains=term)
        | Q(quote__number__icontains=term)
        | Q(supplier_invoice__supplier_name__icontains=term)
        | Q(supplier_invoice__reference__icontains=term)
        | Q(accounting_document__title__icontains=term)
    )
