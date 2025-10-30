"""
Définitions d’URL pour le catalogue de services hérité.

Ce module connecte les vues de liste et de détail à des URLs lisibles.
L’espace de noms reste ``services`` afin de préserver la compatibilité
avec l’app moderne.  Les pages utilisent des images libres de droits
Unsplash par défaut et respectent la charte graphique de 2025.
"""

from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceListView.as_view(), name="list"),
    path("<slug:slug>/", views.ServiceDetailView.as_view(), name="detail"),
]