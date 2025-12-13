"""
Routeur URL pour l'app ``devis``.

Cette configuration expose les routes suivantes :

* ``/devis/nouveau/`` pour soumettre une nouvelle demande de devis.
* ``/devis/succes/`` pour afficher la confirmation après soumission.
* ``/devis/admin/<pk>/`` pour l'éditeur avancé de devis (staff uniquement).
* ``/devis/service/<pk>/`` pour récupérer les infos d'un service en JSON.
"""

from django.urls import path
from . import views


app_name = "devis"

urlpatterns = [
    # Formulaire public de devis respectant le cahier des charges 2025
    path("nouveau/", views.public_devis, name="request_quote"),
    path("succes/", views.quote_success, name="quote_success"),
    # Téléchargement d'un PDF de devis (restreint au staff)
    path("telecharger/<int:pk>/", views.download_quote, name="download"),
    # Éditeur avancé de devis (back-office)
    path("admin/<int:pk>/", views.admin_quote_edit, name="admin_quote_edit"),
    # Endpoint JSON pour récupérer les infos d'un service
    path("service/<int:pk>/", views.service_info, name="service_info"),
]
