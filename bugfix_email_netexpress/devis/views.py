from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.forms import inlineformset_factory
from django.views.decorators.http import require_http_methods

from services.models import Service
from .forms import QuoteRequestForm, QuoteAdminForm
from .models import QuoteRequest, Quote, QuoteRequestPhoto, QuoteValidation
from .quote_to_invoice import QuoteToInvoiceService
from core.services.pdf_generator import render_quote_pdf
from .email_service import send_quote_email
from .forms import QuoteValidationCodeForm


@require_http_methods(["GET", "POST"])
def public_devis(request):
    """Formulaire public : création d'une QuoteRequest."""
    if request.method == "POST":
        form = QuoteRequestForm(request.POST, request.FILES)
        if form.is_valid():
            qr: QuoteRequest = form.save()
            files = form.cleaned_data.get("photos_list") or []
            for f in files:
                photo = QuoteRequestPhoto.objects.create(image=f)
                qr.photos.add(photo)
            messages.success(request, "Votre demande de devis a bien été envoyée.")
            return redirect("devis:quote_success")
    else:
        form = QuoteRequestForm()
    return render(request, "devis/request_quote.html", {"form": form})


def quote_success(request):
    return render(request, "devis/quote_success.html")


@staff_member_required
def download_quote_pdf(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    # Ensure PDF exists (generate & attach)
    if not quote.pdf:
        quote.generate_pdf(attach=True)
    try:
        return FileResponse(quote.pdf.open("rb"), content_type="application/pdf")
    except Exception as exc:
        raise Http404() from exc



@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_quote_edit(request, pk):
    """Éditeur back-office : métadonnées + lignes + actions (PDF / email / conversion)."""
    from django.forms import inlineformset_factory
    from django.core.exceptions import ValidationError
    from .models import QuoteItem
    from .forms import QuoteItemForm

    quote = get_object_or_404(Quote, pk=pk)

    QuoteItemFormSet = inlineformset_factory(
        Quote,
        QuoteItem,
        form=QuoteItemForm,
        fields=("service", "description", "quantity", "unit_price", "tax_rate"),
        extra=1,
        can_delete=True,
    )

    if request.method == "POST":
        form = QuoteAdminForm(request.POST, instance=quote)
        formset = QuoteItemFormSet(request.POST, instance=quote, prefix="items")
        action = request.POST.get("_action")

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()

            # Recompute totals after line changes
            try:
                quote.compute_totals()
            except Exception:
                pass

            # Business validation (ex: forbid SENT/ACCEPTED without lines)
            try:
                quote.full_clean()
            except ValidationError as exc:
                messages.error(request, f"Erreur de validation : {exc}")
                return render(
                    request,
                    "devis/admin_quote_edit.html",
                    {"form": form, "formset": formset, "quote": quote},
                )

            if action == "generate_pdf":
                pdf_res = render_quote_pdf(quote)
                quote.pdf.save(pdf_res.filename, ContentFile(pdf_res.content), save=True)
                messages.success(request, "PDF généré.")
            elif action == "send_email":
                if not quote.pdf:
                    quote.generate_pdf(attach=True)
                send_quote_email(quote, request=request)
                messages.success(
                    request,
                    "Email envoyé (le code de validation sera envoyé séparément après clic sur le lien).",
                )
            elif action == "convert_invoice":
                invoice = QuoteToInvoiceService.convert(quote)
                messages.success(request, f"Converti en facture : {invoice.number}")
                return redirect(f"/admin/factures/invoice/{invoice.pk}/change/")

            return redirect("devis:admin_quote_edit", pk=quote.pk)
    else:
        form = QuoteAdminForm(instance=quote)
        formset = QuoteItemFormSet(instance=quote, prefix="items")

    return render(request, "devis/admin_quote_edit.html", {"form": form, "formset": formset, "quote": quote})

@staff_member_required
def service_info(request, pk):
    srv = get_object_or_404(Service, pk=pk)
    return JsonResponse({
        "id": srv.pk,
        "name": getattr(srv, "name", str(srv)),
        "description": getattr(srv, "description", ""),
        "base_price": str(getattr(srv, "base_price", "")),
        "tax_rate": str(getattr(srv, "tax_rate", "")),
    })

@staff_member_required
def admin_generate_quote_pdf(request, pk):
    quote = get_object_or_404(Quote, pk=pk)

    if hasattr(quote, "generate_pdf"):
        quote.generate_pdf(attach=True)
        messages.success(request, "Devis PDF généré avec succès.")
    else:
        messages.error(request, "La génération PDF n’est pas disponible.")

    return redirect(
        "admin:devis_quote_change",
        object_id=quote.pk,
    )


# ---------------------------------------------------------------------------
# Validation devis (double facteur)
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def quote_validate_start(request, token: str):
    """Étape 1 : lien de validation (public) -> génération + envoi du code.

    Le paramètre ``token`` est le ``Quote.public_token`` (stable).
    """
    quote = get_object_or_404(Quote, public_token=token)
    validation = QuoteValidation.create_for_quote(quote)

    # Envoie le code (email premium HTML) et redirige vers la saisie
    from .email_service import send_quote_validation_code
    send_quote_validation_code(quote, validation)
    return redirect("devis:quote_validate_code", token=validation.token)


@require_http_methods(["GET", "POST"])
def quote_validate_code(request, token: str):
    """Étape 2 : saisie du code -> validation finale."""
    validation = get_object_or_404(QuoteValidation, token=token)
    quote = validation.quote

    if validation.is_expired:
        messages.error(request, "Ce code a expiré. Merci de relancer une validation.")
        return render(request, "quotes/validate_expired.html", {"quote": quote})

    if request.method == "POST":
        form = QuoteValidationCodeForm(request.POST)
        if form.is_valid():
            ok = validation.verify(form.cleaned_data["code"])
            if ok:
                # Statut devis -> accepté
                quote.status = Quote.QuoteStatus.ACCEPTED
                quote.save(update_fields=["status"])
                messages.success(request, "Merci ! Votre devis est validé.")
                return render(request, "quotes/validate_success.html", {"quote": quote})
            messages.error(request, "Code incorrect. Veuillez réessayer.")
    else:
        form = QuoteValidationCodeForm()

    return render(
        request,
        "quotes/validate_code.html",
        {"quote": quote, "form": form, "validation": validation},
    )


@require_http_methods(["GET"])
def quote_public_pdf(request, token: str):
    """Téléchargement public du PDF via un jeton *stable*.

    Historique:
    - v1: le lien pointait vers QuoteValidation.token (peut expirer / être régénéré)
    - v2+: le lien public pointe vers Quote.public_token (stable)
    Pour compatibilité, on accepte encore un token de QuoteValidation si nécessaire.
    """
    quote = None
    # 1) Token public stable du devis
    try:
        quote = Quote.objects.get(public_token=token)
    except Exception:
        quote = None

    # 2) Compatibilité: ancien token de validation 2FA
    if quote is None:
        validation = get_object_or_404(QuoteValidation, token=token)
        if validation.is_expired:
            raise Http404()
        quote = validation.quote

    if not quote.pdf:
        quote.generate_pdf(attach=True)
    try:
        return FileResponse(quote.pdf.open("rb"), content_type="application/pdf")
    except Exception as exc:
        raise Http404() from exc
