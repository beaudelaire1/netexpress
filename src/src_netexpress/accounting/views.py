from decimal import Decimal
from functools import wraps
from tempfile import SpooledTemporaryFile
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from accounts.models import Profile
from accounts.portal import get_user_role
from core.services.email_service import EmailService
from factures.models import Invoice
from .forms import AccountantInvitationForm, AccountingDocumentForm, PeriodForm, ReviewForm, SupplierInvoiceForm
from .models import AccountingActivity, AccountingDocument, InvoiceReview, SupplierInvoice
from .services import (csv_content, incomplete_purchases, invoice_fingerprint, is_reviewed, issued_invoices,
                       log_activity, period_documents, supporting_documents, shared_quotes, period_quotes,
                       invoice_pdf_content, quote_pdf_content, quotes_csv_content)

ADMIN_ROLES = {Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL}


def accounting_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        role = get_user_role(request.user)
        if role not in ADMIN_ROLES | {Profile.ROLE_ACCOUNTANT}:
            return HttpResponseForbidden("Accès réservé au cabinet comptable et aux administrateurs.")
        if role == Profile.ROLE_ACCOUNTANT and not request.user.profile.has_verified_email:
            messages.warning(request, "Activez votre compte grâce au lien d’invitation reçu par email.")
            return redirect("accounts:profile")
        request.accounting_admin = role in ADMIN_ROLES
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response
    return wrapped


def page_context(request, **kwargs):
    return {"accounting_admin": request.accounting_admin, "accounting_reviewer": not request.accounting_admin, **kwargs}


def filtered(request):
    form = PeriodForm(request.GET)
    if not form.is_valid():
        return form, issued_invoices().none(), SupplierInvoice.objects.none()
    return form, *period_documents(form.cleaned_data)


@accounting_required
def dashboard(request):
    form, sales, purchases = filtered(request)
    documents = supporting_documents(form.cleaned_data) if form.is_valid() else AccountingDocument.objects.none()
    quotes = period_quotes(form.cleaned_data) if form.is_valid() else shared_quotes().none()
    totals = {"sales": Decimal(0), "credits": Decimal(0), "sales_vat": Decimal(0), "pending_sales": 0}
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
    totals["reviewed"] = totals["count"] - totals["pending"]
    totals["overdue_purchases"] = purchases.filter(paid_on__isnull=True, due_date__lt=timezone.localdate()).count()
    activities = AccountingActivity.objects.select_related("actor")
    if not request.accounting_admin:
        activities = activities.exclude(action__startswith="Accès cabinet").exclude(action__startswith="Invitation cabinet")
    return render(request, "accounting/dashboard.html", page_context(request, form=form, totals=totals,
        recent_sales=sales[:5], recent_purchases=purchases[:5], recent_documents=documents[:4], recent_quotes=quotes[:4],
        activities=activities[:8]))


@accounting_required
def sales(request):
    form, invoices, _ = filtered(request)
    page = Paginator(invoices, 40).get_page(request.GET.get("page"))
    for invoice in page:
        invoice.accounting_checked = is_reviewed(invoice)
    return render(request, "accounting/sales.html", page_context(request, form=form, page=page))


@accounting_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(issued_invoices(), pk=pk)
    return render(request, "accounting/invoice_detail.html", page_context(request, invoice=invoice,
        checked=is_reviewed(invoice), review=getattr(invoice, "accounting_review", None),
        form=ReviewForm(initial={"fingerprint": invoice_fingerprint(invoice)})))


@accounting_required
@require_POST
@transaction.atomic
def review_invoice(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")
    # Lock the invoice alone: PostgreSQL cannot lock the nullable side of the quote join.
    invoice = get_object_or_404(Invoice.all_objects.select_for_update(), pk=pk, issued_at__isnull=False)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    fingerprint = invoice_fingerprint(invoice)
    if form.cleaned_data["fingerprint"] != fingerprint:
        messages.error(request, "La facture a changé depuis l’ouverture. Relisez-la avant de la comptabiliser.")
    else:
        InvoiceReview.objects.update_or_create(invoice=invoice, defaults={"fingerprint": fingerprint,
            "note": form.cleaned_data["note"], "reviewed_by": request.user, "reviewed_at": timezone.now()})
        log_activity(request.user, "Facture client comptabilisée", invoice.number)
        messages.success(request, "Facture marquée comme comptabilisée.")
    return redirect("accounting:invoice_detail", pk=pk)


@accounting_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(issued_invoices(), pk=pk)
    try:
        content = invoice_pdf_content(invoice)
    except (OSError, ValueError):
        messages.error(request, "Le PDF original est indisponible. Demandez à NetExpress de vérifier la reprise des anciennes factures.")
        return redirect("accounting:invoice_detail", pk=pk)
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{slugify(invoice.number)}.pdf"'
    log_activity(request.user, "Téléchargement facture client", invoice.number)
    return response


@accounting_required
def suppliers(request):
    form, _, purchases = filtered(request)
    if request.GET.get("pending") == "1":
        purchases = purchases.filter(reviewed_at__isnull=True)
    if request.GET.get("incomplete") == "1":
        purchases = incomplete_purchases(purchases)
    total = purchases.aggregate(total=Sum("total_ttc"))["total"] or Decimal(0)
    return render(request, "accounting/suppliers.html", page_context(request, form=form, total=total,
        incomplete_count=incomplete_purchases(purchases).count(),
        page=Paginator(purchases.select_related("created_by"), 40).get_page(request.GET.get("page"))))


@accounting_required
def supplier_edit(request, pk=None):
    if not request.accounting_admin:
        return HttpResponseForbidden("Le dépôt et la modification des pièces sont réservés à NetExpress.")
    instance = get_object_or_404(SupplierInvoice, pk=pk) if pk else SupplierInvoice()
    form = SupplierInvoiceForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                if pk:
                    locked = SupplierInvoice.objects.select_for_update().get(pk=pk)
                    if request.POST.get("version") != locked.updated_at.isoformat():
                        form.add_error(None, "Cette facture a été modifiée. Rechargez la page avant de réessayer.")
                    else:
                        instance.reviewed_at = None
                        instance.reviewed_by = None
                        instance.review_note = ""
                else:
                    instance.created_by = request.user
                if not form.errors:
                    form.save()
                    log_activity(request.user, "Facture fournisseur modifiée" if pk else "Facture fournisseur ajoutée", instance)
                    messages.success(request, "Facture disponible pour le cabinet. " +
                        ("Elle est à vérifier." if instance.is_complete else "Vous pourrez compléter les informations plus tard."))
                    return redirect("accounting:supplier_detail", pk=instance.pk)
        except IntegrityError:
            form.add_error(None, "Cette facture ou cette pièce existe déjà.")
    return render(request, "accounting/supplier_form.html", page_context(request, form=form, purchase=instance))


@accounting_required
def supplier_detail(request, pk):
    purchase = get_object_or_404(SupplierInvoice.objects.select_related("created_by", "reviewed_by"), pk=pk)
    return render(request, "accounting/supplier_detail.html", page_context(request, purchase=purchase,
        form=ReviewForm(initial={"fingerprint": purchase.updated_at.isoformat()})))


@accounting_required
@require_POST
@transaction.atomic
def review_supplier(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")
    purchase = get_object_or_404(SupplierInvoice.objects.select_for_update(), pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    if not purchase.is_complete:
        messages.error(request, "Complétez le fournisseur, le numéro, la date, le TTC et la TVA avant de comptabiliser la facture.")
    elif form.cleaned_data["fingerprint"] != purchase.updated_at.isoformat():
        messages.error(request, "La facture a changé. Relisez-la avant de la comptabiliser.")
    else:
        purchase.reviewed_at = timezone.now()
        purchase.reviewed_by = request.user
        purchase.review_note = form.cleaned_data["note"]
        purchase.save(update_fields=["reviewed_at", "reviewed_by", "review_note", "updated_at"])
        log_activity(request.user, "Facture fournisseur comptabilisée", purchase)
        messages.success(request, "Facture marquée comme comptabilisée.")
    return redirect("accounting:supplier_detail", pk=pk)


@accounting_required
def documents(request):
    form = PeriodForm(request.GET)
    pieces = supporting_documents(form.cleaned_data) if form.is_valid() else AccountingDocument.objects.none()
    kind = request.GET.get("kind", "")
    if kind:
        pieces = pieces.filter(kind=kind)
    if request.GET.get("pending") == "1":
        pieces = pieces.filter(reviewed_at__isnull=True)
    return render(request, "accounting/documents.html", page_context(request, form=form,
        kinds=AccountingDocument.Kind.choices, selected_kind=kind,
        page=Paginator(pieces.select_related("created_by"), 40).get_page(request.GET.get("page"))))


@accounting_required
def document_edit(request, pk=None):
    if not request.accounting_admin:
        return HttpResponseForbidden("Le dépôt et la modification des pièces sont réservés à NetExpress.")
    instance = get_object_or_404(AccountingDocument, pk=pk) if pk else AccountingDocument()
    form = AccountingDocumentForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                if pk:
                    locked = AccountingDocument.objects.select_for_update().get(pk=pk)
                    if request.POST.get("version") != locked.updated_at.isoformat():
                        form.add_error(None, "Ce document a été modifié. Rechargez la page avant de réessayer.")
                    else:
                        instance.reviewed_at = None
                        instance.reviewed_by = None
                        instance.review_note = ""
                else:
                    instance.created_by = request.user
                if not form.errors:
                    form.save()
                    log_activity(request.user, "Document modifié" if pk else "Document ajouté", instance)
                    messages.success(request, "Document enregistré et disponible pour le cabinet.")
                    return redirect("accounting:document_detail", pk=instance.pk)
        except IntegrityError:
            form.add_error(None, "Cette pièce existe déjà.")
    return render(request, "accounting/document_form.html", page_context(request, form=form, document=instance))


@accounting_required
def document_detail(request, pk):
    document = get_object_or_404(AccountingDocument.objects.select_related("created_by", "reviewed_by"), pk=pk)
    return render(request, "accounting/document_detail.html", page_context(request, document=document,
        form=ReviewForm(initial={"fingerprint": document.updated_at.isoformat()})))


@accounting_required
@require_POST
@transaction.atomic
def review_document(request, pk):
    if request.accounting_admin:
        return HttpResponseForbidden("Le contrôle comptable est réservé au cabinet.")
    document = get_object_or_404(AccountingDocument.objects.select_for_update(), pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Note de contrôle invalide.")
    if form.cleaned_data["fingerprint"] != document.updated_at.isoformat():
        messages.error(request, "Le document a changé. Relisez-le avant de le vérifier.")
    else:
        document.reviewed_at = timezone.now()
        document.reviewed_by = request.user
        document.review_note = form.cleaned_data["note"]
        document.save(update_fields=["reviewed_at", "reviewed_by", "review_note", "updated_at"])
        log_activity(request.user, "Document vérifié", document)
        messages.success(request, "Document marqué comme vérifié.")
    return redirect("accounting:document_detail", pk=pk)


@accounting_required
def export_documents(request):
    form, sales, purchases = filtered(request)
    if not form.is_valid():
        return HttpResponseBadRequest("Période invalide.")
    documents = supporting_documents(form.cleaned_data)
    quotes = period_quotes(form.cleaned_data)
    is_zip = request.GET.get("format") == "zip"
    only_quotes = request.GET.get("format") == "quotes"
    limit = 100 if is_zip else 10000
    count = quotes.count() if only_quotes else sales.count() + purchases.count() + documents.count() + (quotes.count() if is_zip else 0)
    if count > limit:
        return HttpResponseBadRequest(f"Limite de {limit} pièces par export. Réduisez la période.")
    name = f"comptabilite-{form.cleaned_data['date_from']}-{form.cleaned_data['date_to']}"
    if only_quotes:
        response = HttpResponse(quotes_csv_content(quotes), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="devis-{name}.csv"'
        log_activity(request.user, "Export devis CSV", name)
        return response
    sales, purchases, documents = list(sales), list(purchases), list(documents)
    csv = csv_content(sales, purchases, documents)
    if not is_zip:
        response = HttpResponse(csv, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{name}.csv"'
    else:
        archive = SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        try:
            size = 0
            with ZipFile(archive, "w", ZIP_DEFLATED) as zipfile:
                zipfile.writestr("journal.csv", csv)
                if quotes.exists():
                    zipfile.writestr("devis.csv", quotes_csv_content(quotes))
                for quote in quotes:
                    content = quote_pdf_content(quote)
                    size += len(content)
                    if size > 100 * 1024 * 1024:
                        raise ValueError("Archive trop volumineuse : réduisez la période (100 Mo maximum).")
                    zipfile.writestr(f"devis/{quote.pk}-{slugify(quote.number)}.pdf", content)
                for invoice in sales:
                    content = invoice_pdf_content(invoice)
                    size += len(content)
                    if size > 100 * 1024 * 1024:
                        raise ValueError("Archive trop volumineuse : réduisez la période (100 Mo maximum).")
                    zipfile.writestr(f"ventes/{invoice.pk}-{slugify(invoice.number)}.pdf", content)
                for piece in purchases + documents:
                    with piece.file.open("rb") as source:
                        content = source.read(10 * 1024 * 1024 + 1)
                    size += len(content)
                    if len(content) > 10 * 1024 * 1024 or size > 100 * 1024 * 1024:
                        raise ValueError("Archive trop volumineuse : réduisez la période (100 Mo maximum).")
                    extension = piece.file.name.rsplit(".", 1)[-1]
                    folder = "achats" if isinstance(piece, SupplierInvoice) else "documents"
                    label = piece.display_name if isinstance(piece, SupplierInvoice) else piece.title
                    zipfile.writestr(f"{folder}/{piece.pk}-{slugify(label)[:60]}.{extension}", content)
            archive.seek(0)
            response = FileResponse(archive, as_attachment=True, filename=name + ".zip")
        except (OSError, ValueError) as exc:
            archive.close()
            messages.error(request, "Export interrompu : pièce indisponible ou limite dépassée. Aucune archive partielle n’a été fournie.")
            return redirect("accounting:dashboard")
        except Exception:
            archive.close()
            raise
    log_activity(request.user, "Export ZIP" if is_zip else "Export CSV", name)
    return response


@accounting_required
def quotes(request):
    form = PeriodForm(request.GET)
    pieces = period_quotes(form.cleaned_data) if form.is_valid() else shared_quotes().none()
    return render(request, "accounting/quotes.html", page_context(request, form=form,
        page=Paginator(pieces, 40).get_page(request.GET.get("page"))))


@accounting_required
def quote_detail(request, pk):
    return render(request, "accounting/quote_detail.html", page_context(request,
        quote=get_object_or_404(shared_quotes(), pk=pk)))


@accounting_required
def quote_pdf(request, pk):
    quote = get_object_or_404(shared_quotes(), pk=pk)
    response = HttpResponse(quote_pdf_content(quote), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{slugify(quote.number)}.pdf"'
    log_activity(request.user, "Téléchargement devis", quote.number)
    return response


@accounting_required
def accountants(request):
    if not request.accounting_admin:
        return HttpResponseForbidden("Seuls les administrateurs gèrent les accès du cabinet.")
    form = AccountantInvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = get_user_model().objects.create_user(username="cabinet_" + uuid4().hex[:16],
                email=data["email"], first_name=data["first_name"], last_name=data["last_name"])
            profile = user.profile
            profile.role = Profile.ROLE_ACCOUNTANT
            profile.accounting_firm = data["accounting_firm"]
            profile.save(update_fields=["role", "accounting_firm"])
            log_activity(request.user, "Accès cabinet créé", user.email)
        sent = EmailService.send_client_portal_invitation(user, request=request)
        if sent:
            messages.success(request, "Invitation envoyée. Le membre choisira son mot de passe via le lien sécurisé.")
        else:
            messages.warning(request, "Compte créé, mais envoi impossible. Vous pouvez renvoyer l’invitation ci-dessous.")
        return redirect("accounting:accountants")
    users = get_user_model().objects.filter(profile__role=Profile.ROLE_ACCOUNTANT).select_related("profile").order_by("email")
    return render(request, "accounting/accountants.html", page_context(request, form=form, accountants=users))


@accounting_required
@require_POST
def accountant_action(request, pk):
    if not request.accounting_admin:
        return HttpResponseForbidden("Accès administrateur requis.")
    user = get_object_or_404(get_user_model(), pk=pk, profile__role=Profile.ROLE_ACCOUNTANT)
    action = request.POST.get("action")
    if action in {"disable", "enable"}:
        user.is_active = action == "enable"
        user.save(update_fields=["is_active"])
        log_activity(request.user, "Accès cabinet réactivé" if user.is_active else "Accès cabinet désactivé", user.email)
        messages.success(request, "Accès mis à jour.")
    elif action == "resend" and user.is_active:
        from django.core.cache import cache
        if not cache.add(f"activation:{user.pk}", True, timeout=300):
            messages.info(request, "Patientez cinq minutes avant de renvoyer une invitation.")
        elif EmailService.send_client_portal_invitation(user, request=request):
            log_activity(request.user, "Invitation cabinet renvoyée", user.email)
            messages.success(request, "Invitation renvoyée.")
        else:
            messages.error(request, "Envoi impossible. Vérifiez la configuration email.")
    else:
        return HttpResponseBadRequest("Action invalide.")
    return redirect("accounting:accountants")
