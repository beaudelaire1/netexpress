"""
Configuration des routes URL pour l’app ``quotes``.

Cette app utilise l’espace de noms ``quotes`` afin de permettre
l’inversion des URLs sans ambiguïté dans les templates.  À partir de
2025, les chemins ont été conservés mais les pages qu’ils renvoient
affichent des illustrations libres de droits issues d’Unsplash【668280112401708†L16-L63】.
"""

from django.urls import path
from . import views

app_name = "quotes"

urlpatterns = [
    path("", views.request_quote, name="request_quote"),
    path("merci/", views.quote_success, name="quote_success"),
]