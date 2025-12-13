"""
Vues pour le formulaire de contact.
Compatibles avec contact/urls.py :
 - contact_view
 - contact_success
"""

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import ContactForm


def contact_view(request):
    """
    Formulaire de contact.
    - Sauvegarde du message via ContactForm()
    - Redirection vers la page de succès
    """

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre message a bien été envoyé.")
            return redirect(reverse("contact:success"))
    else:
        form = ContactForm()

    return render(request, "contact/contact.html", {"form": form})


def contact_success(request):
    """
    Page de confirmation après envoi du formulaire.
    Affiche les informations de contact du branding des factures (optionnel).
    """

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}

    # Si address_lines n'existe pas, on le reconstruit proprement
    if branding and not branding.get("address_lines") and branding.get("address"):
        lines = [
            line.strip()
            for line in str(branding.get("address")).splitlines()
            if line.strip()
        ]
        branding["address_lines"] = lines

    return render(request, "contact/contact_success.html", {"branding": branding})
