"""Vues principales de l'application ``core``.

Ces vues fournissent :
  - une page d'accueil marketing utilisant le thème existant ;
  - une page "à propos" statique ;
  - un endpoint de santé JSON pour le monitoring ;
  - un tableau de bord agrégé pour le back‑office.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

from services.models import Service, Category
from devis.models import Quote
from factures.models import Invoice
from tasks.models import Task
from messaging.models import EmailMessage


def home(request):
    """Page d'accueil publique."""
    categories = Category.objects.all().order_by("name")
    featured_services = (
        Service.objects.filter(is_active=True)
        .order_by("-created_at")[:6]
    )
    return render(
        request,
        "core/home.html",
        {
            "categories": categories,
            "featured_services": featured_services,
        },
    )


def about(request):
    """Page de présentation de l'entreprise."""
    return render(request, "core/about.html")


def excellence(request):
    """
    Page de mise en avant des engagements de l'entreprise.

    Cette vue ne nécessite pas de logique complexe ; elle se contente
    d'afficher un template statique décrivant les valeurs et la
    philosophie de NetExpress.
    """
    return render(request, "core/excellence.html")


def realisations(request):
    """
    Galerie des réalisations.  Les images sont définies statiquement
    car aucune base de données n'est prévue pour cette page dans le
    cahier des charges.  Chaque entrée contient une URL distante
    hébergée par Unsplash, un titre et une catégorie pour le filtrage
    côté client.
    """
    # Images locales (pas d'URL externes) pour éviter les liens morts et
    # améliorer la fiabilité/perf.  Ce jeu d'images est provisoire :
    # l'utilisateur pourra remplacer les fichiers dans static/img/realisations/.
    images = [
        {"path": "img/realisations/espaces_verts_1.jpg", "title": "Villa Montjoly", "category": "espaces_verts"},
        {"path": "img/realisations/nettoyage_1.jpg", "title": "Résidence Kourou", "category": "nettoyage"},
        {"path": "img/realisations/renovation_1.png", "title": "Appartement Cayenne", "category": "renovation"},
        {"path": "img/realisations/espaces_verts_2.jpg", "title": "Jardin Tropical Remire", "category": "espaces_verts"},
        {"path": "img/realisations/nettoyage_2.jpg", "title": "Bureaux Centre-ville", "category": "nettoyage"},
        {"path": "img/realisations/renovation_2.png", "title": "Rafraîchissement Peinture", "category": "renovation"},
    ]
    categories = [
        ("all", "Toutes"),
        ("nettoyage", "Nettoyage"),
        ("espaces_verts", "Espaces verts"),
        ("renovation", "Rénovation"),
    ]
    return render(
        request,
        "core/realisations.html",
        {
            "images": images,
            "categories": categories,
        },
    )


def health(request):
    """Endpoint simple pour les probes de monitoring."""
    return JsonResponse({"status": "ok"})


@staff_member_required
def dashboard(request):
    """Tableau de bord interne agrégé."""
    tasks = Task.objects.all().order_by("-created_at")[:5]
    quotes = Quote.objects.all().order_by("-issue_date")[:5]
    invoices = Invoice.objects.all().order_by("-issue_date")[:5]
    email_messages = EmailMessage.objects.all().order_by("-created_at")[:5]

    return render(
        request,
        "core/dashboard.html",
        {
            "tasks": tasks,
            "quotes": quotes,
            "invoices": invoices,
            "recent_messages": email_messages,
        },
    )
