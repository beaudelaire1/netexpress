"""CRUD, document download and access-management views for accounting.

The day-to-day accountant workspace lives in :mod:`accounting.workspace`.
This module deliberately keeps preparation actions and document access
separate from the dashboard so that draft operational data never leaks into
the cabinet workflow.
"""
from functools import wraps
from tempfile import SpooledTemporaryFile
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from accounts.models import Profile
from accounts.portal import get_user_role
from core.services.email_service import EmailService
from .filters import filtered_documents
from .forms import (
    AccountantInvitationForm,
    AccountingDocumentForm,
    PeriodForm,
    ReviewForm,
    SupplierInvoiceForm,
)
from .models import AccountingDocument, SupplierInvoice
from .services import (
    complete_purchases,
    csv_content,
    invoice_fingerprint,
    invoice_pdf_content,
    is_reviewed,
    issued_invoices,
    log_activity,
    period_documents,
    quote_pdf_content,
    shared_quotes,
    supporting_documents,
)

ADMIN_ROLES = {Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL}


def accounting_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        role = get_user_role(request.user)
        if role not in ADMIN_ROLES | {Profile.ROLE_ACCOUNTANT}:
            return HttpResponseForbidden(
                "Accès réservé au cabinet comptable et aux administrateurs."
            )
        if role == Profile.ROLE_ACCOUNTANT and not request.user.profile.has_verified_email:
            messages.warning(
                request,
                "Activez votre compte grâce au lien d’invitation reçu par email.",
            )
            return redirect("accounts:profile")
        request.accounting_admin = role in ADMIN_ROLES
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return wrapped


def page_context(request, **kwargs):
    return {
        "accounting_admin": request.accounting_admin,
        "accounting_reviewer": not request.accounting_admin,
        **kwargs,
    }


def filtered(request):
    """Return period-filtered pieces with role-aware supplier visibility."""
    form = PeriodForm(request.GET)
    if not form.is_valid():
        return form, issued_invoices().none(), SupplierInvoice.objects.none()

    sales, purchases = period_documents(form.cleaned_data)
    if not request.accounting_admin:
        purchases = complete_purchases(purchases)
    return form, sales, purchases


@accounting_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(issued_invoices(), pk=pk)
    return render(
        request,
        "accounting/invoice_detail.html",
        page_context(
            request,
            invoice=invoice,
            checked=is_reviewed(invoice),
            review=getattr(invoice, "accounting_review", None),
            form=ReviewForm(initial={"fingerprint": invoice_fingerprint(invoice)}),
        ),
    )


@accounting_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(issued_invoices(), pk=pk)
    try:
        content = invoice_pdf_content(invoice)
    except (OSError, ValueError):
        messages.error(
            request,
            "Le PDF original est indisponible. Demandez à NetExpress de vérifier la reprise des anciennes factures.",
        )
        return redirect("accounting:invoice_detail", pk=pk)
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{slugify(invoice.number)}.pdf"'
    log_activity(request.user, "Téléchargement facture client", invoice.number)
    return response


@accounting_required
def supplier_edit(request, pk=None):
    if not request.accounting_admin:
        return HttpResponseForbidden(
            "Le dépôt et la modification des pièces sont réservés à NetExpress."
        )

    instance = get_object_or_404(SupplierInvoice, pk=pk) if pk else SupplierInvoice()
    form = SupplierInvoiceForm(
        request.POST or None,
        request.FILES or None,
        instance=instance,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                if pk:
                    locked = SupplierInvoice.objects.select_for_update().get(pk=pk)
                    if request.POST.get("version") != locked.updated_at.isoformat():
                        form.add_error(
                            None,
                            "Cette facture a été modifiée. Rechargez la page avant de réessayer.",
                        )
                    else:
                        instance.reviewed_at = None
                        instance.reviewed_by = None
                        instance.review_note = ""
                else:
                    instance.created_by = request.user

                if not form.errors:
                    form.save()
                    log_activity(
                        request.user,
                        "Facture fournisseur modifiée"
                        if pk
                        else "Facture fournisseur ajoutée",
                        instance,
                    )
                    if instance.is_complete:
                        messages.success(
                            request,
                            "Facture complète : elle est maintenant disponible dans la file du cabinet.",
                        )
                    else:
                        messages.success(
                            request,
                            "Pièce enregistrée côté NetExpress. Le cabinet ne la verra qu’une fois les informations minimales complétées.",
                        )
                    return redirect("accounting:supplier_detail", pk=instance.pk)
        except IntegrityError:
            form.add_error(None, "Cette facture ou cette pièce existe déjà.")

    return render(
        request,
        "accounting/supplier_form.html",
        page_context(request, form=form, purchase=instance),
    )


@accounting_required
def supplier_detail(request, pk):
    purchases = SupplierInvoice.objects.select_related("created_by", "reviewed_by")
    if not request.accounting_admin:
        purchases = complete_purchases(purchases)
    purchase = get_object_or_404(purchases, pk=pk)
    return render(
        request,
        "accounting/supplier_detail.html",
        page_context(
            request,
            purchase=purchase,
            form=ReviewForm(initial={"fingerprint": purchase.updated_at.isoformat()}),
        ),
    )


@accounting_required
def documents(request):
    """List supporting documents with a single métier filter system."""
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
def document_edit(request, pk=None):
    if not request.accounting_admin:
        return HttpResponseForbidden(
            "Le dépôt et la modification des pièces sont réservés à NetExpress."
        )

    instance = get_object_or_404(AccountingDocument, pk=pk) if pk else AccountingDocument()
    form = AccountingDocumentForm(
        request.POST or None,
        request.FILES or None,
        instance=instance,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                if pk:
                    locked = AccountingDocument.objects.select_for_update().get(pk=pk)
                    if request.POST.get("version") != locked.updated_at.isoformat():
                        form.add_error(
                            None,
                            "Ce document a été modifié. Rechargez la page avant de réessayer.",
                        )
                    else:
                        instance.reviewed_at = None
                        instance.reviewed_by = None
                        instance.review_note = ""
                else:
                    instance.created_by = request.user
                if not form.errors:
                    form.save()
                    log_activity(
                        request.user,
                        "Document modifié" if pk else "Document ajouté",
                        instance,
                    )
                    messages.success(
                        request,
                        "Document enregistré et disponible pour le cabinet.",
                    )
                    return redirect("accounting:document_detail", pk=instance.pk)
        except IntegrityError:
            form.add_error(None, "Cette pièce existe déjà.")

    return render(
        request,
        "accounting/document_form.html",
        page_context(request, form=form, document=instance),
    )


@accounting_required
def document_detail(request, pk):
    document = get_object_or_404(
        AccountingDocument.objects.select_related("created_by", "reviewed_by"),
        pk=pk,
    )
    return render(
        request,
        "accounting/document_detail.html",
        page_context(
            request,
            document=document,
            form=ReviewForm(initial={"fingerprint": document.updated_at.isoformat()}),
        ),
    )


@accounting_required
def export_documents(request):
    """Export only pieces that are actually ready for accounting work."""
    form, sales, purchases = filtered(request)
    if not form.is_valid():
        return HttpResponseBadRequest("Période invalide.")

    # Even company administrators receive an accounting-ready export. Draft
    # supplier uploads belong to preparation, not to the cabinet package.
    purchases = complete_purchases(purchases)
    documents = supporting_documents(form.cleaned_data)
    is_zip = request.GET.get("format") == "zip"
    limit = 100 if is_zip else 10000
    count = sales.count() + purchases.count() + documents.count()
    if count > limit:
        return HttpResponseBadRequest(
            f"Limite de {limit} pièces par export. Réduisez la période."
        )

    name = (
        f"comptabilite-{form.cleaned_data['date_from']}-{form.cleaned_data['date_to']}"
    )
    sales_list = list(sales)
    purchases_list = list(purchases)
    documents_list = list(documents)
    journal = csv_content(sales_list, purchases_list, documents_list)

    if not is_zip:
        response = HttpResponse(journal, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{name}.csv"'
    else:
        archive = SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        try:
            size = 0
            with ZipFile(archive, "w", ZIP_DEFLATED) as zipfile:
                zipfile.writestr("journal.csv", journal)

                for invoice in sales_list:
                    content = invoice_pdf_content(invoice)
                    size += len(content)
                    if size > 100 * 1024 * 1024:
                        raise ValueError(
                            "Archive trop volumineuse : réduisez la période (100 Mo maximum)."
                        )
                    zipfile.writestr(
                        f"ventes/{invoice.pk}-{slugify(invoice.number)}.pdf",
                        content,
                    )

                for piece in purchases_list + documents_list:
                    with piece.file.open("rb") as source:
                        content = source.read(10 * 1024 * 1024 + 1)
                    size += len(content)
                    if (
                        len(content) > 10 * 1024 * 1024
                        or size > 100 * 1024 * 1024
                    ):
                        raise ValueError(
                            "Archive trop volumineuse : réduisez la période (100 Mo maximum)."
                        )
                    extension = piece.file.name.rsplit(".", 1)[-1]
                    folder = "achats" if isinstance(piece, SupplierInvoice) else "documents"
                    label = (
                        piece.display_name
                        if isinstance(piece, SupplierInvoice)
                        else piece.title
                    )
                    zipfile.writestr(
                        f"{folder}/{piece.pk}-{slugify(label)[:60]}.{extension}",
                        content,
                    )

            archive.seek(0)
            response = FileResponse(archive, as_attachment=True, filename=name + ".zip")
        except (OSError, ValueError):
            archive.close()
            messages.error(
                request,
                "Export interrompu : pièce indisponible ou limite dépassée. Aucune archive partielle n’a été fournie.",
            )
            return redirect("accounting:dashboard")
        except Exception:
            archive.close()
            raise

    log_activity(request.user, "Export ZIP" if is_zip else "Export CSV", name)
    return response


@accounting_required
def quote_detail(request, pk):
    """Show a quote only when it explains a cabinet-visible invoice."""
    return render(
        request,
        "accounting/quote_detail.html",
        page_context(request, quote=get_object_or_404(shared_quotes(), pk=pk)),
    )


@accounting_required
def quote_pdf(request, pk):
    """Download the contextual quote attached to a cabinet-visible invoice."""
    quote = get_object_or_404(shared_quotes(), pk=pk)
    response = HttpResponse(quote_pdf_content(quote), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{slugify(quote.number)}.pdf"'
    log_activity(request.user, "Téléchargement devis lié", quote.number)
    return response


@accounting_required
def accountants(request):
    if not request.accounting_admin:
        return HttpResponseForbidden(
            "Seuls les administrateurs gèrent les accès du cabinet."
        )

    form = AccountantInvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username="cabinet_" + uuid4().hex[:16],
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
            )
            profile = user.profile
            profile.role = Profile.ROLE_ACCOUNTANT
            profile.accounting_firm = data["accounting_firm"]
            profile.save(update_fields=["role", "accounting_firm"])
            log_activity(request.user, "Accès cabinet créé", user.email)

        sent = EmailService.send_client_portal_invitation(user, request=request)
        if sent:
            messages.success(
                request,
                "Invitation envoyée. Le membre choisira son mot de passe via le lien sécurisé.",
            )
        else:
            messages.warning(
                request,
                "Compte créé, mais envoi impossible. Vous pouvez renvoyer l’invitation ci-dessous.",
            )
        return redirect("accounting:accountants")

    users = (
        get_user_model()
        .objects.filter(profile__role=Profile.ROLE_ACCOUNTANT)
        .select_related("profile")
        .order_by("email")
    )
    return render(
        request,
        "accounting/accountants.html",
        page_context(request, form=form, accountants=users),
    )


@accounting_required
@require_POST
def accountant_action(request, pk):
    if not request.accounting_admin:
        return HttpResponseForbidden("Accès administrateur requis.")

    user = get_object_or_404(
        get_user_model(),
        pk=pk,
        profile__role=Profile.ROLE_ACCOUNTANT,
    )
    action = request.POST.get("action")
    if action in {"disable", "enable"}:
        user.is_active = action == "enable"
        user.save(update_fields=["is_active"])
        log_activity(
            request.user,
            "Accès cabinet réactivé" if user.is_active else "Accès cabinet désactivé",
            user.email,
        )
        messages.success(request, "Accès mis à jour.")
    elif action == "resend" and user.is_active:
        from django.core.cache import cache

        if not cache.add(f"activation:{user.pk}", True, timeout=300):
            messages.info(
                request,
                "Patientez cinq minutes avant de renvoyer une invitation.",
            )
        elif EmailService.send_client_portal_invitation(user, request=request):
            log_activity(request.user, "Invitation cabinet renvoyée", user.email)
            messages.success(request, "Invitation renvoyée.")
        else:
            messages.error(request, "Envoi impossible. Vérifiez la configuration email.")
    else:
        return HttpResponseBadRequest("Action invalide.")

    return redirect("accounting:accountants")
