"""
Vues pour l'app ``contact``.

Le formulaire de contact permet aux visiteurs d'envoyer des messages
structurés (sujets prédéfinis).  Lors de la soumission, un enregistrement
``Message`` est créé et éventuellement une notification par e‑mail est
envoyée (en fonction de votre configuration SMTP).  Depuis la refonte
de 2025, la mise en page du formulaire suit la charte graphique de
NetExpress et rappelle que toutes les illustrations proviennent de
sources libres de droits telles qu'Unsplash【668280112401708†L16-L63】.
"""

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

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
            messages.success(request, "Merci pour votre message. Nous reviendrons vers vous rapidement.")
            return redirect(reverse("contact:contact"))
    else:
        form = ContactForm()
    return render(request, "contact/contact.html", {"form": form})