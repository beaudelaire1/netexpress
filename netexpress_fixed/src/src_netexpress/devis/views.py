"""Vues pour l'application ``devis``."""

from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.forms import inlineformset_factory
from django.http import FileResponse, Http404, JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
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
                quote_request.photos.add(photo)
            # Envoi d'un courriel de confirmation au client et à l'admin
            subject = "Votre demande de devis a bien été reçue"
            logo_url = request.build_absolute_uri(static("img/logo.png"))
            cta_url = request.build_absolute_uri(reverse("devis:request_quote"))

            # Contexte email brandé (HTML uniquement)
            context = {
                "quote_request": quote_request,
                "logo_url": logo_url,
                "cta_url": cta_url,
                "cta_label": "Accéder à la page Devis",
                "brand_name": getattr(settings, "INVOICE_BRANDING", {}).get("name", "Nettoyage Express"),
                "website_url": getattr(settings, "INVOICE_BRANDING", {}).get("website", ""),
                "instagram_url": getattr(settings, "INVOICE_BRANDING", {}).get("instagram", ""),
                "facebook_url": getattr(settings, "INVOICE_BRANDING", {}).get("facebook", ""),
            }
            html_message = render_to_string("emails/new_quote.html", context)

            # Destinataires
            recipients = [quote_request.email]
            admin_emails = [email for _, email in getattr(settings, "ADMINS", []) or []]
            task_admin = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
            if task_admin:
                admin_emails.append(task_admin)
            for e in admin_emails:
                if e and e not in recipients:
                    recipients.append(e)

            try:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body="",  # jamais de texte brut
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    to=recipients,
                )
                email.attach_alternative(html_message, "text/html")
                email.send(fail_silently=True)
            except Exception:
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
        form = QuoteAdminForm(request.POST, instance=quote)
        formset = QuoteItemFormSet(request.POST, instance=quote)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            # Recalcul des totaux côté serveur
            if hasattr(quote, "compute_totals") and callable(getattr(quote, "compute_totals")):
                quote.compute_totals()  # type: ignore[call-arg]
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
