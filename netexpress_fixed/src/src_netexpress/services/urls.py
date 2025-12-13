"""
URL configuration pour le module ``services``.

Cette configuration expose deux routes :

* ``/services/`` affiche la liste des services actifs, avec la possibilité de
  filtrer par catégorie via un paramètre de requête ``?category=slug``.
* ``/services/<slug>/`` affiche la page de détail d'un service identifié par
  son slug.

Les routes utilisent l'espace de noms ``services`` pour éviter toute
ambiguïté lors de l'utilisation de ``{% url %}`` dans les templates.  Elles
restent identiques en 2025 mais les gabarits associés ont été remaniés afin
d'intégrer des images libres de droits comme illustration.
"""

from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceListView.as_view(), name="list"),
    path("<slug:slug>/", views.ServiceDetailView.as_view(), name="detail"),
]