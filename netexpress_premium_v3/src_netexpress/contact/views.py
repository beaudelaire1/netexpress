"""
Vues pour le formulaire de contact.

- Sauvegarde du message
- Notification admin asynchrone via Celery
- Contexte JS : correspondance Commune <-> Code postal (Guyane)
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import ContactForm
from .tasks import notify_new_contact


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
        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save()

            # Email admin asynchrone
            try:
                notify_new_contact.delay(msg.pk)
            except Exception:
                # Fallback synchrone si Celery n'est pas disponible
                try:
                    notify_new_contact(msg.pk)
                except Exception:
                    pass

            messages.success(request, "Votre message a bien été envoyé.")
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
    return render(request, "contact/contact_success.html", {})
