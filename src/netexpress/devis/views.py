"""
Vues pour l'app ``devis``.

Ces vues gèrent l'affichage du formulaire de demande de devis et la page de
confirmation après soumission.  Le formulaire est basé sur ``DevisForm`` qui
crée un ``Client`` et un ``Quote`` lors de l'enregistrement.

L'implémentation a été revue afin d'offrir un parcours plus fluide et de
pré‑remplir le service demandé lorsque celui‑ci est transmis dans l'URL.
En cas de dépendances manquantes (par exemple si Django n'est pas disponible),
le fichier ``manage.py`` lance un serveur statique minimaliste permettant
d'accéder à l'interface utilisateur.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import FileResponse, Http404
from django.contrib.admin.views.decorators import staff_member_required

from .forms import DevisForm

# Importer la fonction de notification de devis depuis l'app messaging si disponible.
try:
    from messaging.services import send_quote_notification  # type: ignore
except Exception:
    send_quote_notification = None  # type: ignore


def request_quote(request):
    """
    Afficher et traiter le formulaire de demande de devis.

    Sur requête GET, un formulaire vierge est rendu.  Si un paramètre de
    requête ``service`` est présent (par exemple depuis la page d'un service),
    il est utilisé pour pré‑sélectionner le service dans le formulaire.

    Sur POST, les données sont validées et un devis est créé.  Un message de
    succès est affiché et l'utilisateur est redirigé vers la page de
    confirmation.
    """
    initial_data = {}
    service_slug = request.GET.get("service")
    if service_slug:
        # Pré‑sélectionner le service par slug si possible
        from services.models import Service
        try:
            initial_data["service"] = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            pass
    if request.method == "POST":
        form = DevisForm(request.POST, request.FILES)
        if form.is_valid():
            # Enregistrer la demande et récupérer l'instance pour notification
            quote = form.save()
            # Sauvegarder les photos téléchargées
            for uploaded in request.FILES.getlist("images"):
                try:
                    from .models import QuotePhoto
                    QuotePhoto.objects.create(quote=quote, image=uploaded)
                except Exception:
                    pass
            # Envoyer une notification e‑mail si le service est disponible
            if send_quote_notification:
                try:
                    send_quote_notification(quote)
                except Exception:
                    # Ne pas bloquer l'envoi en cas d'erreur
                    pass
            messages.success(
                request,
                "Votre demande de devis a été envoyée avec succès. Nous vous contacterons rapidement.",
            )
            return redirect(reverse("devis:quote_success"))
    else:
        form = DevisForm(initial=initial_data)
    return render(request, "devis/request_quote.html", {"form": form})


def quote_success(request):
    """Afficher une simple page de remerciement après l'envoi d'un devis."""
    return render(request, "devis/quote_success.html")

# -----------------------------------------------------------------------------
# Téléchargement du PDF d'un devis
# -----------------------------------------------------------------------------

@staff_member_required
def download_quote(request, pk: int):
    """Servir le fichier PDF associé à un devis pour les membres du staff.

    Cette vue renvoie une 404 si le devis n'existe pas ou si aucun PDF n'a
    encore été généré.  L'affichage en ligne permet au navigateur de
    prévisualiser le document sans forcer le téléchargement.
    """
    from .models import Quote
    quote = get_object_or_404(Quote, pk=pk)
    if not quote.pdf:
        raise Http404("Ce devis n'a pas encore été généré.")
    return FileResponse(quote.pdf.open("rb"), filename=quote.pdf.name, as_attachment=False)