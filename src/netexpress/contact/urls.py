"""
Routes URL pour l'app ``contact`` (version 2025).

Une seule route est exposée afin de servir le formulaire de contact.  Le
nom de l'espace de noms est ``contact`` pour faciliter les appels via
``{% url %}`` dans les templates.  Cette app a été revue pour
assurer une validation obligatoire du numéro de téléphone et une
mise en page harmonisée avec les autres pages.  Les visuels du site
utilisent des images libres de droits grâce à Unsplash【668280112401708†L16-L63】.
"""

from django.urls import path
from . import views

app_name = "contact"

urlpatterns = [
    path("", views.contact_view, name="contact"),
]