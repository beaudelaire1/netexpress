"""
Vues pour le formulaire de contact.

- Sauvegarde du message
- Notification interne au gestionnaire (voir ``contact.tasks``)
- Contexte JS : correspondance Commune <-> Code postal (Guyane)
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import ContactForm
from .tasks import notify_new_contact

# Clé de session servant à transmettre le récapitulatif du message à la page
# de confirmation. Un redirect ne peut rien porter d'autre, et repasser
# l'identifiant dans l'URL exposerait les messages des autres visiteurs.
CONTACT_CONFIRMATION_SESSION_KEY = "contact_confirmation"


GUYANE_COMMUNES = {
    "Apatou": "97317",
    "Awala-Yalimapo": "97319",
    "Camopi": "97330",
    "Cayenne": "97300",
    "Grand Santi": "97340",
    "Iracoubo": "97350",
    "Kourou": "97310",
    "Macouria": "97355",
    "Mana": "97360",
    "Maripasoula": "97370",
    "Matoury": "97351",
    "Montsinéry": "97356",
    "Ouanary": "97380",
    "Papaïchton": "97316",
    "Régina": "97390",
    "Rémire-Montjoly": "97354",
    "Roura": "97311",
    "Saint-Elie": "97312",
    "Saint-Georges de l'Oyapock": "97313",
    "Saint-Laurent du Maroni": "97320",
    "Saül": "97314",
    "Sinnamary": "97315",
}


def contact_view(request):
    if request.method == "POST":
        # Vérification Cloudflare Turnstile
        from core.turnstile import verify_turnstile
        if not verify_turnstile(request):
            messages.error(request, "Vérification de sécurité échouée. Veuillez réessayer.")
            form = ContactForm(request.POST)
            return render(request, "contact/contact.html", {"form": form, "communes": GUYANE_COMMUNES})

        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save()

            # Le message est enregistré : un échec d'envoi est journalisé côté
            # serveur, pas répercuté sur le visiteur, dont la demande est bien
            # arrivée.
            notify_new_contact(msg.pk)

            request.session[CONTACT_CONFIRMATION_SESSION_KEY] = {
                "reference": f"MSG-{msg.pk:05d}",
                "first_name": msg.full_name.split(" ")[0],
                "email": msg.email,
                "topic": msg.get_topic_display(),
            }
            return redirect(reverse("contact:success"))
    else:
        form = ContactForm()

    return render(
        request,
        "contact/contact.html",
        {
            "form": form,
            "communes": GUYANE_COMMUNES,
        },
    )


def contact_success(request):
    # Consommé une seule fois : un rechargement de la page ne doit pas
    # ré-afficher un accusé de réception qui n'a plus lieu d'être.
    confirmation = request.session.pop(CONTACT_CONFIRMATION_SESSION_KEY, None)

    return render(
        request,
        "contact/contact_success.html",
        {
            "confirmation": confirmation,
            "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
        },
    )
