"""Vues pour l'application ``devis``."""

import logging
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

logger = logging.getLogger(__name__)


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
                quote_request.photos.add(photo)

            # Envoi asynchrone de confirmation (HTML brandé)
            # Avec fallback synchrone si Celery est indisponible
            try:
                from devis.tasks import send_quote_request_received
                send_quote_request_received.delay(quote_request.pk)
                logger.info("Tâche Celery créée pour QuoteRequest %s", quote_request.pk)
            except Exception as e:
                logger.warning("Celery indisponible pour QuoteRequest %s: %s. Tentative synchrone.", quote_request.pk, e)
                # Fallback synchrone
                try:
                    from django.conf import settings
                    from django.core.mail import EmailMessage
                    from django.template.loader import render_to_string

                    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
                    site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
                    html = render_to_string("emails/new_quote.html", {
                        "quote_request": quote_request,
                        "branding": branding,
                        "cta_url": site_url.rstrip("/") + "/devis/demande/",
                    })
                    email = EmailMessage(
                        subject="Votre demande de devis a bien été reçue",
                        body=html,
                        to=[quote_request.email],
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    )
                    email.content_subtype = "html"
                    email.send(fail_silently=True)
                    logger.info("Email synchrone envoyé pour QuoteRequest %s", quote_request.pk)
                except Exception as sync_error:
                    logger.exception("Envoi synchrone également échoué: %s", sync_error)

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
                logger.debug("Totaux recalculés pour devis %s", quote.number)
            except Exception as e:
                logger.exception("Échec compute_totals pour devis %s: %s", quote.pk, e)

            # Si le devis passe à "Envoyé", on génère le PDF et on envoie au client
            if quote.status == Quote.QuoteStatus.SENT and prev_status != Quote.QuoteStatus.SENT:
                # Génération PDF
                try:
                    from django.core.files.base import ContentFile
                    from core.services.pdf_generator import render_quote_pdf
                    pdf_res = render_quote_pdf(quote)
                    quote.pdf.save(pdf_res.filename, ContentFile(pdf_res.content), save=True)
                    logger.info("PDF généré et sauvegardé pour devis %s", quote.number)
                except Exception as e:
                    logger.exception("Échec génération PDF pour devis %s: %s", quote.pk, e)

                # Envoi email via Celery avec fallback synchrone
                try:
                    from devis.tasks import send_quote_pdf_email
                    send_quote_pdf_email.delay(quote.pk)
                    logger.info("Tâche Celery créée pour envoi devis %s", quote.number)
                except Exception as e:
                    logger.warning("Celery indisponible pour devis %s: %s. Tentative synchrone.", quote.pk, e)
                    # Fallback synchrone
                    try:
                        from core.services.email_service import PremiumEmailService
                        email_service = PremiumEmailService()
                        email_service.send_quote_pdf_to_client(quote)
                        logger.info("Email devis %s envoyé en synchrone", quote.number)
                    except Exception as sync_error:
                        logger.exception("Envoi synchrone également échoué pour devis %s: %s", quote.pk, sync_error)

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
    """Servir le fichier PDF associé à un devis pour le staff."""
    quote = get_object_or_404(Quote, pk=pk)
    if not quote.pdf:
        raise Http404("Ce devis n'a pas encore été généré.")
    return FileResponse(quote.pdf.open("rb"), filename=quote.pdf.name, as_attachment=False)
