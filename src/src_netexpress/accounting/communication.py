"""Compatibilité de l'ancien raccourci « Écrire à NetExpress ».

Les nouveaux échanges passent par le domaine comptable dédié. Cette vue reste
présente pour ne pas casser un formulaire ou un favori issu de la version
précédente du portail.
"""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .exchange_services import create_exchange
from .models import AccountingExchange
from .views import accounting_required

MAX_ACCOUNTING_MESSAGE_LENGTH = 4000


@accounting_required
@require_POST
def send_message_to_netexpress(request):
    if request.accounting_admin:
        return HttpResponseForbidden(
            "Cette action est réservée au cabinet comptable externe."
        )

    raw_message = (request.POST.get("message") or "").strip()
    if not raw_message:
        messages.error(request, "Rédigez un message avant l’envoi.")
        return redirect("accounting:exchange_create")
    if len(raw_message) > MAX_ACCOUNTING_MESSAGE_LENGTH:
        messages.error(
            request,
            f"Le message est limité à {MAX_ACCOUNTING_MESSAGE_LENGTH} caractères.",
        )
        return redirect("accounting:exchange_create")

    firm = (getattr(request.user.profile, "accounting_firm", "") or "").strip()
    exchange = create_exchange(
        request.user,
        subject=f"Message du cabinet — {firm or 'Espace comptable'}"[:200],
        kind=AccountingExchange.Kind.QUESTION,
        priority=AccountingExchange.Priority.NORMAL,
        content=raw_message,
    )
    messages.success(request, "Message converti en échange comptable traçable.")
    return redirect("accounting:exchange_detail", pk=exchange.pk)
