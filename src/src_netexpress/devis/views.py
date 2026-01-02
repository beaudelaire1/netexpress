"""Vues pour l'application ``devis``."""

from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.http import FileResponse, Http404, JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from services.models import Service
from .forms import DevisForm, QuoteRequestForm, QuoteAdminForm, QuoteItemForm
from .models import Quote, QuoteItem, QuoteRequest


def request_quote(request: HttpRequest) -> HttpResponse:
    """Afficher et traiter le formulaire public de demande de devis.

    Cette vue crée une :class:`QuoteRequest` sans générer immédiatement
    de devis chiffré. Les éventuelles photos sont associées via un
    modèle intermédiaire.
    """
    if request.method == "POST":
        form = QuoteRequestForm(request.POST, request.FILES)
        if form.is_valid():
            quote_request = form.save()
            # Gestion des fichiers uploadés
            files = request.FILES.getlist("photos")
            from .models import QuoteRequestPhoto  # import local pour éviter cycles
            for f in files:
                photo = QuoteRequestPhoto.objects.create(image=f)
                quote_request.photos.add(photo)            # Envoi asynchrone de confirmation (HTML brandé)
            try:
                from devis.tasks import send_quote_request_received
                send_quote_request_received.delay(quote_request.pk)
            except Exception:
                # Ne bloque jamais le flux utilisateur si Celery est indisponible
                pass
            return redirect(reverse("devis:quote_success"))
    else:
        form = QuoteRequestForm()

    return render(request, "devis/request_quote.html", {"form": form})


def public_devis(request: HttpRequest) -> HttpResponse:
    """
    Formulaire de devis pour le grand public conforme au cahier des charges 2025.

    Ce formulaire utilise :class:`DevisForm` avec des champs
    supplémentaires (type de service, surface en m², niveau d'urgence).
    À la validation, un ``Quote`` et un ``Client`` sont créés puis
    enregistrés via la méthode ``save`` du formulaire.  Aucune photo
    n'est gérée ici.
    """
    from .forms import DevisForm
    # Pré-remplissage depuis la home (GET) : service_type, surface, urgency
    initial = {}
    if request.method == "GET":
        for key in ("service_type", "surface", "urgency"):
            val = request.GET.get(key)
            if val:
                initial[key] = val

    if request.method == "POST":
        form = DevisForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect(reverse("devis:quote_success"))
    else:
        form = DevisForm(initial=initial)
    return render(request, "devis/devis_form.html", {"form": form})


def quote_success(request: HttpRequest) -> HttpResponse:
    """Page de confirmation après dépôt d'une demande de devis."""
    return render(request, "devis/quote_success.html", {})


@login_required
@staff_member_required
def admin_quote_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Éditeur avancé de devis pour le back‑office.

    - Permet de modifier les métadonnées du devis (client, dates, statut).
    - Permet d'ajouter / supprimer des lignes (:class:`QuoteItem`).
    - Calcule les totaux côté client en JavaScript, avec vérification
      supplémentaire côté serveur via ``compute_totals``.
    """
    quote = get_object_or_404(Quote, pk=pk)

    QuoteItemFormSet = inlineformset_factory(
        Quote,
        QuoteItem,
        form=QuoteItemForm,
        extra=0,
        can_delete=True,
    )

    if request.method == "POST":
        prev_status = quote.status
        form = QuoteAdminForm(request.POST, instance=quote)
        formset = QuoteItemFormSet(request.POST, instance=quote)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            # Recalcul des totaux + génération PDF
            try:
                quote.compute_totals()
            except Exception:
                pass

            # Si le devis passe à "Envoyé", on génère le PDF et on envoie au client (Celery)
            try:
                if quote.status == Quote.QuoteStatus.SENT and prev_status != Quote.QuoteStatus.SENT:
                    from django.core.files.base import ContentFile
                    from core.services.pdf_generator import render_quote_pdf
                    pdf_res = render_quote_pdf(quote)
                    quote.pdf.save(pdf_res.filename, ContentFile(pdf_res.content), save=True)
                    from devis.tasks import send_quote_pdf_email
                    send_quote_pdf_email.delay(quote.pk)
            except Exception:
                pass

            return redirect(reverse("devis:admin_quote_edit", args=[quote.pk]))
    else:
        form = QuoteAdminForm(instance=quote)
        formset = QuoteItemFormSet(instance=quote)

    context = {
        "quote": quote,
        "form": form,
        "formset": formset,
    }
    return render(request, "devis/admin_quote_edit.html", context)


@login_required
@staff_member_required
def service_info(request: HttpRequest, pk: int) -> JsonResponse:
    """Retourne des informations JSON sur un service.

    Utilisé par l'éditeur de devis pour préremplir la description
    lorsqu'un service est sélectionné.
    """
    service = get_object_or_404(Service, pk=pk)
    data = {
        "id": service.pk,
        "title": service.title,
        "description": service.description,
        "unit_type": service.unit_type,
    }
    return JsonResponse(data)


@staff_member_required
def download_quote(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Servir le fichier PDF associé à un devis pour le staff.
    Si le fichier PDF n'existe pas ou n'est pas accessible (système éphémère),
    le régénère à la volée.
    """
    quote = get_object_or_404(Quote, pk=pk)
    
    # Vérifier si le PDF existe et est accessible
    pdf_exists = False
    if quote.pdf:
        try:
            # Tenter d'ouvrir le fichier pour vérifier qu'il existe réellement
            quote.pdf.open("rb")
            quote.pdf.close()
            pdf_exists = True
        except (FileNotFoundError, OSError, IOError):
            # Le fichier n'existe pas (système éphémère) ou n'est pas accessible
            pdf_exists = False
    
    # Si le PDF n'existe pas, le régénérer à la volée
    if not pdf_exists:
        try:
            # Régénérer le PDF sans l'attacher (pour éviter d'écrire sur le système éphémère)
            pdf_bytes = quote.generate_pdf(attach=False)
            # Construire le nom du fichier
            filename = f"{quote.number or 'devis'}.pdf"
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except Exception as e:
            raise Http404(f"Impossible de générer le PDF du devis : {str(e)}")
    
    return FileResponse(quote.pdf.open("rb"), filename=quote.pdf.name, as_attachment=False)
