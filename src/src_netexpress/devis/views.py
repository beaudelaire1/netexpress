from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.forms import inlineformset_factory
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from services.models import Service
from .forms import QuoteRequestForm, QuoteAdminForm, QuoteItemForm, QuoteValidationCodeForm
from .models import QuoteRequest, Quote, QuoteItem, QuoteRequestPhoto, QuoteValidation
from .services import create_invoice_from_quote
from core.services.document_generator import DocumentGenerator
from .email_service import send_quote_email
from .tasks import notify_new_quote_request
from devis.application.quote_validation import (
    QuoteNotValidatableError,
    QuoteValidationExpiredError,
    confirm_quote_validation_code,
    start_quote_validation,
)

logger = logging.getLogger(__name__)

# Clé de session servant à transmettre le récapitulatif à la page de
# confirmation. Un redirect ne peut rien porter d'autre, et repasser
# l'identifiant dans l'URL exposerait les demandes des autres visiteurs.
QUOTE_CONFIRMATION_SESSION_KEY = "quote_confirmation"


@require_http_methods(["GET", "POST"])
def public_devis(request):
    """Formulaire public : création d'une QuoteRequest."""
    if request.method == "POST":
        from core.turnstile import verify_turnstile

        if not verify_turnstile(request):
            from django.contrib import messages as msg

            msg.error(request, "Vérification de sécurité échouée. Veuillez réessayer.")
            form = QuoteRequestForm(request.POST, request.FILES)
            return render(request, "devis/request_quote.html", {"form": form})

        form = QuoteRequestForm(request.POST, request.FILES)
        if form.is_valid():
            qr: QuoteRequest = form.save()
            files = form.cleaned_data.get("photos_list") or []
            for f in files:
                photo = QuoteRequestPhoto.objects.create(image=f)
                qr.photos.add(photo)
            # La demande est enregistrée : un échec d'envoi est journalisé
            # côté serveur, pas répercuté sur le visiteur.
            notify_new_quote_request(qr.pk)

            request.session[QUOTE_CONFIRMATION_SESSION_KEY] = {
                "reference": f"REQ-{qr.pk:05d}",
                "first_name": qr.client_name.split(" ")[0],
                "email": qr.email,
                "service": qr.get_service_type_display(),
                "deadline": qr.get_deadline_display(),
                "photos": qr.photos.count(),
            }
            return redirect("devis:quote_success")
    else:
        valid_services = dict(QuoteRequest.ServiceType.choices)
        valid_deadlines = dict(QuoteRequest.Deadline.choices)
        initial = {}

        service_type = request.GET.get("service_type")
        if service_type in valid_services:
            initial["service_type"] = service_type

        surface = request.GET.get("surface")
        if surface and surface.isdigit():
            initial["surface"] = int(surface)

        urgency = request.GET.get("urgency") or request.GET.get("deadline")
        if urgency in valid_deadlines:
            initial["deadline"] = urgency

        form = QuoteRequestForm(initial=initial)
    return render(request, "devis/request_quote.html", {"form": form})


def quote_success(request):
    # Consommé une seule fois : un rechargement ne doit pas ré-afficher un
    # accusé de réception qui n'a plus lieu d'être.
    confirmation = request.session.pop(QUOTE_CONFIRMATION_SESSION_KEY, None)

    return render(
        request,
        "devis/quote_success.html",
        {
            "confirmation": confirmation,
            "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
        },
    )


@staff_member_required
def download_quote_pdf(request, pk):
    """Génère et affiche une version fraîche du devis PDF."""
    quote = get_object_or_404(Quote, pk=pk)
    try:
        pdf_bytes = quote.generate_pdf(attach=False)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="devis_{quote.number}.pdf"'
        response["Cache-Control"] = "private, no-store"
        return response
    except Exception as exc:
        logger.error(
            "Erreur lors de la génération du PDF pour le devis %s: %s",
            pk,
            exc,
            exc_info=True,
        )
        raise Http404("Impossible de générer le PDF du devis")


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_quote_edit(request, pk):
    """Éditeur complet : métadonnées, lignes, totaux et actions documentaires."""
    from smtplib import SMTPAuthenticationError

    quote = get_object_or_404(Quote, pk=pk)
    QuoteItemFormSet = inlineformset_factory(
        Quote,
        QuoteItem,
        form=QuoteItemForm,
        extra=0,
        can_delete=True,
    )

    if request.method == "POST":
        form = QuoteAdminForm(request.POST, instance=quote)
        formset = QuoteItemFormSet(request.POST, instance=quote)
        action = request.POST.get("_action", "save")

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            quote.compute_totals()

            if action == "generate_pdf":
                quote.generate_pdf(attach=True)
                messages.success(request, "PDF généré.")
            elif action == "send_email":
                # Toujours régénérer pour éviter l'envoi d'un document obsolète.
                quote.generate_pdf(attach=True)
                try:
                    send_quote_email(quote, request=request)
                    messages.success(request, "Email envoyé.")
                except SMTPAuthenticationError:
                    messages.error(
                        request,
                        "Authentification SMTP refusée par Brevo. Vérifiez BREVO_SMTP_LOGIN/BREVO_SMTP_PASSWORD ou configurez BREVO_API_KEY.",
                    )
                except Exception as exc:
                    messages.error(request, f"Erreur envoi email: {exc}")
            elif action == "convert_invoice":
                result = create_invoice_from_quote(quote)
                invoice = result.invoice
                messages.success(request, f"Converti en facture : {invoice.number}")
                return redirect(f"/admin/factures/invoice/{invoice.pk}/change/")
            else:
                messages.success(request, "Devis enregistré.")

            return redirect("devis:admin_quote_edit", pk=quote.pk)
    else:
        form = QuoteAdminForm(instance=quote)
        formset = QuoteItemFormSet(instance=quote)

    return render(
        request,
        "devis/admin_quote_edit.html",
        {"form": form, "formset": formset, "quote": quote},
    )


@staff_member_required
def service_info(request, pk):
    srv = get_object_or_404(Service, pk=pk)
    title = getattr(srv, "title", None) or getattr(srv, "name", None) or str(srv)
    return JsonResponse(
        {
            "id": srv.pk,
            "title": title,
            "description": getattr(srv, "description", ""),
            "unit_type": getattr(srv, "unit_type", ""),
            "base_price": str(getattr(srv, "base_price", "") or ""),
            "tax_rate": str(getattr(srv, "tax_rate", "") or ""),
        }
    )


@staff_member_required
def admin_generate_quote_pdf(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if hasattr(quote, "generate_pdf"):
        quote.generate_pdf(attach=True)
        messages.success(request, "Devis PDF généré avec succès.")
    else:
        messages.error(request, "La génération PDF n’est pas disponible.")

    return redirect("admin:devis_quote_change", object_id=quote.pk)


# ---------------------------------------------------------------------------
# Validation devis (double facteur)
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def quote_validate_start(request, token: str):
    """Étape 1 : lien de validation public -> génération et envoi du code."""
    quote = get_object_or_404(Quote, public_token=token)
    try:
        res = start_quote_validation(quote, request=request)
    except QuoteNotValidatableError:
        messages.error(request, "Ce devis ne peut pas être validé dans son état actuel.")
        return redirect("devis:quote_success")
    return redirect("devis:quote_validate_code", token=res.validation.token)


@require_http_methods(["GET", "POST"])
def quote_validate_code(request, token: str):
    """Étape 2 : saisie du code -> validation finale."""
    validation = get_object_or_404(QuoteValidation, token=token)
    quote = validation.quote

    if validation.is_expired:
        messages.error(request, "Ce code a expiré. Merci de relancer une validation.")
        return render(request, "devis/validate_expired.html", {"quote": quote})

    if request.method == "POST":
        form = QuoteValidationCodeForm(request.POST)
        if form.is_valid():
            try:
                ok = confirm_quote_validation_code(
                    validation=validation,
                    submitted_code=form.cleaned_data["code"],
                )
            except QuoteValidationExpiredError:
                messages.error(request, "Ce code a expiré. Merci de relancer une validation.")
                return render(request, "devis/validate_expired.html", {"quote": quote})

            if ok:
                messages.success(request, "Merci ! Votre devis est validé.")
                return render(request, "devis/validate_success.html", {"quote": quote})

            messages.error(request, "Code incorrect. Veuillez réessayer.")
    else:
        form = QuoteValidationCodeForm()

    return render(
        request,
        "devis/validate_code.html",
        {"quote": quote, "form": form, "validation": validation},
    )


@require_http_methods(["GET"])
def quote_public_pdf(request, token: str):
    """Téléchargement public du PDF via un jeton stable ou un ancien jeton 2FA."""
    quote = None
    try:
        quote = Quote.objects.get(public_token=token)
    except Exception:
        quote = None

    if quote is None:
        validation = get_object_or_404(QuoteValidation, token=token)
        if validation.is_expired:
            raise Http404()
        quote = validation.quote

    try:
        pdf_bytes = quote.generate_pdf(attach=False)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Cache-Control"] = "private, no-store"
        response["Content-Disposition"] = f'inline; filename="devis_{quote.number}.pdf"'
        return response
    except Exception as exc:
        logger.error(
            "Erreur lors de la génération du PDF public pour le token %s: %s",
            token,
            exc,
            exc_info=True,
        )
        raise Http404("Impossible de générer le PDF du devis")
