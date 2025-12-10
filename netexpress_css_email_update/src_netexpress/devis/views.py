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
                quote_request.photos.add(photo)
            # Envoi d'un courriel de confirmation au client et à l'admin
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.conf import settings
            from django.templatetags.static import static
            # Sujet et contenu HTML
            subject = "Votre demande de devis a bien été reçue"
            logo_url = request.build_absolute_uri(static('img/logo.png'))
            history_url = request.build_absolute_uri(reverse('devis:request_quote'))
            context = {"quote_request": quote_request, "logo_url": logo_url, "history_url": history_url}
            html_message = render_to_string("emails/new_quote.html", context)
            recipient_list = [quote_request.email]
            # Ajouter l'email d'admin comme destinataire secondaire si défini
            admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
            if admin_email:
                recipient_list.append(admin_email)
            try:
                send_mail(
                    subject=subject,
                    message="",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_list,
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception:
                # L'envoi d'email ne doit pas bloquer le flux utilisateur
                pass
            return redirect(reverse("devis:quote_success"))
    else:
        form = QuoteRequestForm()

    return render(request, "devis/request_quote.html", {"form": form})


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
