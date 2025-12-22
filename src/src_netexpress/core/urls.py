"""
Routes de l'application ``core``.

Cette configuration définit les chemins de l'accueil, d'une route de santé
pour les sondes de monitoring et de la page À propos.  Les chemins
utilisent un espace de noms afin de faciliter leur utilisation dans les
templates.
"""

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Page d'accueil
    path("", views.home, name="home"),
    # Endpoint de monitoring, renvoie un JSON simple
    path("health/", views.health, name="health"),
    # Page "À propos" selon le cahier des charges
    path("a-propos/", views.about, name="about"),
    # Page "L'Excellence" dédiée aux valeurs de l'entreprise
    path("excellence/", views.excellence, name="excellence"),
    # Galerie de réalisations avec filtrage et lightbox
    path("realisations/", views.realisations, name="realisations"),
    # Tableau de bord agrégé
    path("dashboard/", views.dashboard, name="dashboard"),
    # Protection fichiers media (devis, factures PDF)
    path("media/<path:path>", views.protected_media, name="protected_media"),
]