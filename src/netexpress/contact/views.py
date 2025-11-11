"""
Vues pour l'app ``contact``.

    Le formulaire de contact permet aux visiteurs d'envoyer des messages
    structurés (sujets prédéfinis).  Lors de la soumission, un enregistrement
    ``Message`` est créé et éventuellement une notification par e‑mail est
    envoyée (en fonction de votre configuration SMTP).  Depuis la refonte
    de 2025, la mise en page du formulaire suit la charte graphique de
    NetExpress et rappelle que toutes les illustrations proviennent
    désormais du dossier local ``static/img``.  Ainsi, le projet ne
    dépend plus d'images libres de droits externes comme Unsplash【668280112401708†L16-L63】.
"""

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from messaging.models import EmailMessage

from .forms import ContactForm

try:
    # Importer la fonction de notification si la messagerie est installée
    from messaging.services import send_contact_notification  # type: ignore
except Exception:
    send_contact_notification = None  # type: ignore


def contact_view(request):
    """
    Afficher et traiter le formulaire de contact.

    Sur GET, un formulaire vierge est rendu.  Sur POST, les données sont
    validées et un message est enregistré.  Un message flash remercie
    l'utilisateur et le redirige vers la même page afin de vider le formulaire.
    """
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            # Stocker l'adresse IP si disponible
            message.ip = request.META.get("REMOTE_ADDR")
            message.save()
            # Envoyer une notification par e‑mail si le service est disponible
            if send_contact_notification:
                try:
                    send_contact_notification(message)
                except Exception:
                    # Ignorer les erreurs d'envoi afin de ne pas bloquer la soumission du formulaire
                    pass
            # Rediriger vers la page de remerciement plutôt que de revenir
            # sur le formulaire.  La vue de succès affichera les
            # coordonnées de l'entreprise.
            return redirect(reverse("contact:success"))
    else:
        form = ContactForm()
    return render(request, "contact/contact.html", {"form": form})

# -----------------------------------------------------------------------------
# Page de remerciement après soumission du formulaire de contact
# -----------------------------------------------------------------------------
from django.conf import settings
try:
    # Utiliser la fonction utilitaire de l'app factures pour découper l'adresse
    from factures.models import _get_branding  # type: ignore
except Exception:
    _get_branding = None  # type: ignore


def contact_success(request):
    """Afficher une page de remerciement avec les coordonnées de l'entreprise.

    Cette vue est accessible après l'envoi d'un message via le formulaire de
    contact.  Elle affiche le nom de l'entreprise, son adresse postale et
    ses numéros de téléphone (fixe et mobile) à partir des paramètres
    ``INVOICE_BRANDING``.  L'adresse e‑mail n'est volontairement pas affichée
    afin de privilégier un contact téléphonique.
    """
    # Construire un dictionnaire de branding cohérent.
    if _get_branding:
        branding = _get_branding()
    else:
        branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
        # Fallback : si address_lines n'existe pas, découper l'adresse en lignes
        if branding and not branding.get("address_lines") and branding.get("address"):
            lines = [line.strip() for line in str(branding.get("address")).splitlines() if line.strip()]
            branding["address_lines"] = lines
    return render(request, "contact/contact_success.html", {"branding": branding})