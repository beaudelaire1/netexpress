"""
Routeur URL pour l'app ``devis``.

Cette configuration expose deux routes :

* ``/devis/nouveau/`` pour soumettre une nouvelle demande de devis.
* ``/devis/succes/`` pour afficher la confirmation après soumission.

L'app est déclarée avec ``app_name = 'devis'`` afin de permettre l'utilisation
d'espaces de noms dans les ``{% url %}`` des templates.
"""

from django.urls import path
from . import views


app_name = "devis"

urlpatterns = [
    path("nouveau/", views.request_quote, name="request_quote"),
    path("succes/", views.quote_success, name="quote_success"),
    # Téléchargement d'un PDF de devis (restreint au staff)
    path("telecharger/<int:pk>/", views.download_quote, name="download"),
]