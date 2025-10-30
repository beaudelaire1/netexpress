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
]