from __future__ import annotations

from django import template
from django.db.models import Exists, OuterRef

from accounts.models import Profile
from accounts.portal import get_user_role
from accounting.exchange_services import context_meta, unread_exchange_count
from accounting.models import (
    AccountingExchange,
    AccountingExchangeDocument,
    AccountingExchangeReadState,
)

register = template.Library()


def _waiting_status_for_user(user):
    role = get_user_role(user)
    if role in {Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL}:
        return AccountingExchange.Status.WAITING_NETEXPRESS
    return AccountingExchange.Status.WAITING_ACCOUNTANT


@register.simple_tag
def accounting_exchange_nav(user):
    if not getattr(user, "is_authenticated", False):
        return {"unread": 0, "waiting": 0, "open": 0}
    queryset = AccountingExchange.objects.all()
    return {
        "unread": unread_exchange_count(user),
        "waiting": queryset.filter(status=_waiting_status_for_user(user)).count(),
        "open": queryset.exclude(status=AccountingExchange.Status.RESOLVED).count(),
    }


@register.simple_tag
def accounting_exchange_dashboard(user, accounting_admin=False):
    if not getattr(user, "is_authenticated", False):
        return {"unread": 0, "waiting": 0, "open": 0, "recent": [], "documents": []}

    read_state = AccountingExchangeReadState.objects.filter(
        exchange_id=OuterRef("pk"),
        user=user,
        last_read_at__gte=OuterRef("last_activity_at"),
    )
    queryset = AccountingExchange.objects.select_related(
        "invoice__client",
        "quote__client",
        "supplier_invoice",
        "accounting_document",
        "created_by",
    ).annotate(is_read=Exists(read_state))
    recent = list(queryset[:4])
    for exchange in recent:
        exchange.context_meta = context_meta(exchange)

    documents = AccountingExchangeDocument.objects.select_related(
        "exchange", "uploaded_by"
    )
    if not accounting_admin:
        documents = documents.filter(
            visibility=AccountingExchangeDocument.Visibility.SHARED
        )

    return {
        "unread": unread_exchange_count(user),
        "waiting": queryset.filter(status=_waiting_status_for_user(user)).count(),
        "open": queryset.exclude(status=AccountingExchange.Status.RESOLVED).count(),
        "recent": recent,
        "documents": list(documents[:3]),
    }


@register.simple_tag
def accounting_exchange_context(obj):
    manager = getattr(obj, "accounting_exchanges", None)
    if manager is None:
        return {"open_count": 0, "total": 0, "recent": []}
    queryset = manager.select_related("created_by").all()
    return {
        "open_count": queryset.exclude(status=AccountingExchange.Status.RESOLVED).count(),
        "total": queryset.count(),
        "recent": list(queryset[:3]),
    }
