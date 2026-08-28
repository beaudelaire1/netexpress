"""Communication directe du cabinet vers NetExpress depuis l'espace comptable."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import escape, linebreaks
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import Profile
from messaging.models import Message

from .services import log_activity
from .views import accounting_required

MAX_ACCOUNTING_MESSAGE_LENGTH = 4000


def _netexpress_recipient():
    """Choisit un destinataire interne actif sans l'exposer au cabinet."""
    users = get_user_model().objects.filter(is_active=True)
    for role in (Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL):
        recipient = users.filter(profile__role=role).order_by("pk").first()
        if recipient is not None:
            return recipient
    return None


def _safe_return_url(request) -> str:
    candidate = (request.POST.get("next") or "").strip()
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse("accounting:dashboard")


@accounting_required
@require_POST
def send_message_to_netexpress(request):
    """Envoie un message interne, en texte libre échappé, au responsable NetExpress."""
    if request.accounting_admin:
        return HttpResponseForbidden(
            "Cette action est réservée au cabinet comptable externe."
        )

    return_url = _safe_return_url(request)
    raw_message = (request.POST.get("message") or "").strip()

    if not raw_message:
        messages.error(request, "Rédigez un message avant l'envoi.")
        return redirect(return_url)

    if len(raw_message) > MAX_ACCOUNTING_MESSAGE_LENGTH:
        messages.error(
            request,
            f"Le message est limité à {MAX_ACCOUNTING_MESSAGE_LENGTH} caractères.",
        )
        return redirect(return_url)

    recipient = _netexpress_recipient()
    if recipient is None:
        messages.error(
            request,
            "Aucun destinataire NetExpress actif n'est configuré. Contactez l'administrateur.",
        )
        return redirect(return_url)

    firm = (getattr(request.user.profile, "accounting_firm", "") or "").strip()
    subject = f"Espace comptable — {firm or 'Message du cabinet'}"[:200]

    # Les vues de messagerie historique affichent le contenu HTML avec |safe.
    # On échappe donc systématiquement le texte saisi avant d'ajouter les retours ligne.
    safe_content = linebreaks(escape(raw_message), autoescape=False)
    Message.objects.create(
        sender=request.user,
        recipient=recipient,
        subject=subject,
        content=safe_content,
    )

    log_activity(request.user, "Message cabinet envoyé", "NetExpress")
    messages.success(request, "Message transmis à NetExpress.")
    return redirect(return_url)
