"""
Vues pour l’app ``quotes`` (demandes de devis).

Deux endpoints sont exposés : un pour soumettre une nouvelle demande et
un autre pour afficher une page de remerciement après la soumission.  Le
formulaire est construit à partir du modèle ``Quote`` et stylé selon la
charte NetExpress.  La refonte de 2025 a ajouté des messages flash
conviviaux et mentionne que les images visibles sur ces pages sont
issues d’Unsplash【668280112401708†L16-L63】.
"""

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from .forms import QuoteForm


def request_quote(request):
    """
    Display and process the quote request form.

    On GET requests a blank form is rendered.  On POST the form is
    validated and, if valid, the quote is saved to the database.  A success
    message is displayed to the user and they are redirected to a thank you
    page.
    """
    initial_data = {}
    # Pre-fill the service field if passed as query parameter (e.g. from service detail)
    service_name = request.GET.get("service")
    if service_name:
        initial_data["service"] = service_name
    if request.method == "POST":
        form = QuoteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre demande de devis a été envoyée avec succès. Nous vous contacterons rapidement.")
            return redirect(reverse("quotes:quote_success"))
    else:
        form = QuoteForm(initial=initial_data)
    return render(request, "quotes/request_quote.html", {"form": form})


def quote_success(request):
    """Render a simple thank you page after a quote has been submitted."""
    return render(request, "quotes/quote_success.html")