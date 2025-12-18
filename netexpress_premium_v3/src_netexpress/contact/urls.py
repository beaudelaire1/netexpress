"""
Routes URL pour l'app ``contact`` (version 2025).

Une seule route est exposée afin de servir le formulaire de contact.
Le nom de l'espace de noms est ``contact`` pour faciliter les appels via
``{% url %}`` dans les templates.  Cette app a été revue pour
assurer une validation obligatoire du numéro de téléphone et une
mise en page harmonisée avec les autres pages.  Les visuels du site
utilisent désormais uniquement des images locales (``static/img``)
et ne dépendent plus de banques libres comme Unsplash.
"""

from django.urls import path
from . import views

app_name = "contact"

urlpatterns = [
    path("", views.contact_view, name="contact"),
    # Page de remerciement après l'envoi du formulaire de contact
    path("merci/", views.contact_success, name="success"),
]