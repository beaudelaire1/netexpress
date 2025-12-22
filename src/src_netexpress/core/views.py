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


from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.conf import settings


@login_required
def protected_media(request, path):
    """
    Sert les fichiers media avec protection d'authentification.

    Cette vue empêche l'accès direct aux fichiers sensibles (devis, factures PDF)
    sans authentification. Seuls les utilisateurs connectés avec les bonnes permissions
    peuvent accéder aux fichiers.

    Args:
        request: HttpRequest Django
        path: Chemin relatif du fichier dans MEDIA_ROOT

    Returns:
        FileResponse si autorisé, sinon PermissionDenied ou Http404

    Exemple:
        URL: /media/protected/factures/FAC-2025-001.pdf
        → Vérifie que l'utilisateur est staff
        → Retourne le fichier si autorisé
    """
    import os
    from pathlib import Path

    # Protection des dossiers sensibles
    if path.startswith(('devis/', 'factures/', 'quote_requests/')):
        # Seuls les staff peuvent accéder aux documents commerciaux
        if not request.user.is_staff:
            raise PermissionDenied("Vous n'avez pas accès à ce fichier.")

    # Construction du chemin absolu
    file_path = Path(settings.MEDIA_ROOT) / path

    # Vérification existence fichier
    if not file_path.exists() or not file_path.is_file():
        raise Http404("Fichier non trouvé.")

    # Sécurité: empêcher path traversal (../)
    try:
        file_path = file_path.resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        # Vérifier que le fichier est bien dans MEDIA_ROOT
        if not str(file_path).startswith(str(media_root)):
            raise PermissionDenied("Accès interdit.")
    except Exception:
        raise PermissionDenied("Chemin invalide.")

    # Servir le fichier
    try:
        response = FileResponse(file_path.open('rb'), as_attachment=False)
        # Définir le nom de fichier pour le téléchargement
        response['Content-Disposition'] = f'inline; filename="{file_path.name}"'
        return response
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lecture fichier {path}: {e}")
        raise Http404("Erreur lors de la lecture du fichier.")
