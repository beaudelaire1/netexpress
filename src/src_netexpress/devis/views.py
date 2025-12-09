"""Vues pour l'application ``devis``."""

from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required

from .forms import DevisForm
from .models import Quote


def request_quote(request):
    """Afficher et traiter le formulaire de demande de devis."""
    if request.method == "POST":
        form = DevisForm(request.POST, request.FILES)
        if form.is_valid():
            quote = form.save()
            request.session["last_quote_id"] = quote.pk
            return redirect(reverse("devis:quote_success"))
    else:
        form = DevisForm()

    return render(request, "devis/request_quote.html", {"form": form})


def quote_success(request):
    """Page de confirmation après création d'un devis."""
    quote = None
    last_id = request.session.pop("last_quote_id", None)
    if last_id is not None:
        quote = Quote.objects.filter(pk=last_id).first()
    return render(request, "devis/quote_success.html", {"quote": quote})


@staff_member_required
def download_quote(request, pk: int):
    """Servir le fichier PDF associé à un devis pour le staff."""
    quote = get_object_or_404(Quote, pk=pk)
    if not quote.pdf:
        raise Http404("Ce devis n'a pas encore été généré.")
    return FileResponse(quote.pdf.open("rb"), filename=quote.pdf.name, as_attachment=False)
