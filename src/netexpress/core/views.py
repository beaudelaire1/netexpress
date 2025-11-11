"""
Vues de l'application ``core``.

  * ``home`` : rend la page d'accueil avec une sélection de services en
    vedette et la liste des catégories.  La mise en page a été repensée en
    2025 pour inclure des visuels locaux libres de droits (dossier
    ``static/img``) et assurer une meilleure expérience utilisateur.  Les
    dépendances à des banques d'images externes comme Unsplash ont été
    supprimées.
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
from tasks.models import Task
from factures.models import Invoice
from devis.models import Quote

try:
    # Importer la messagerie uniquement si l'application est installée
    from messaging.models import EmailMessage  # type: ignore
except Exception:
    EmailMessage = None  # type: ignore


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


def dashboard(request):
    """Render a simple dashboard aggregating tasks, invoices and quotes.

    This view provides an overview of the current workload and recent
    commercial documents.  Tasks are ordered by due date, while
    invoices and quotes are truncated to the five most recent entries.
    The dashboard can be extended in the future to include charts,
    statistics or filters.
    """
    tasks = Task.objects.all().order_by("due_date")
    invoices = Invoice.objects.order_by("-issue_date")[:5]
    quotes = Quote.objects.order_by("-issue_date")[:5]
    # Inclure quelques messages récents dans le tableau de bord si la messagerie est disponible
    # Récupérer quelques messages récents si l'application de messagerie est disponible.
    if EmailMessage:
        email_messages = list(EmailMessage.objects.order_by("-created_at")[:5])
    else:
        email_messages = []
    # Use a distinct context key for recent messages to avoid clashing with
    # Django's built-in message framework.  Previously the context used
    # "messages", which shadowed the built-in messages in base.html and
    # prevented flash notifications from showing on the dashboard.
    return render(
        request,
        "core/dashboard.html",
        {
            "tasks": tasks,
            "invoices": invoices,
            "quotes": quotes,
            "recent_messages": email_messages,
        },
    )