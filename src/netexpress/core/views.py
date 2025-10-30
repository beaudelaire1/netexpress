"""
Vues de l'application ``core``.

* ``home`` : rend la page d'accueil avec une sélection de services en
  vedette et la liste des catégories.  La mise en page a été repensée en
  2025 pour inclure des visuels libres de droits (Unsplash) et assurer
  une meilleure expérience utilisateur.
* ``about`` : rend une page de présentation de l'entreprise, détaillant ses
  valeurs et sa mission.  Cette page met également en avant la nouvelle
  interface et l'utilisation d'images libres de droits.
* ``health`` : renvoie un simple JSON pour les probes de monitoring.

Ces vues restent volontairement simples et ne dépendent pas de modules
externes afin de garantir une compatibilité maximale, même lorsque Django
n'est pas installé【668280112401708†L16-L63】.
"""

from django.shortcuts import render
from django.http import JsonResponse
from services.models import Service, Category


def home(request):
    """
    Render the landing page. A handful of active services are selected to be
    displayed as highlights.  Adjust the number of services shown here to
    customise the homepage.
    """
    # Fetch a few active services to showcase on the homepage. We also
    # retrieve all service categories to display a "Nos métiers" section.
    featured = Service.objects.filter(is_active=True).order_by("title")[:6]
    categories = Category.objects.all().order_by("name")
    return render(request, "home.html", {
        "featured_services": featured,
        "categories": categories,
    })


def about(request):
    """
    Render a simple "À propos" page describing the company.  This page
    outlines the mission, values et l’historique de l’entreprise selon le
    cahier de charge.  It can be customised in the template
    ``core/about.html``.
    """
    return render(request, "core/about.html")


def health(request):
    """Simple JSON endpoint used by uptime probes to check application health."""
    return JsonResponse({"status": "ok"})