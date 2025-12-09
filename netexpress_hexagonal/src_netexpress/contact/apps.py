"""
Configuration de l'application ``contact``.

L'application gère la collecte des messages clients via un formulaire.  Le
verbose_name a été ajusté afin de refléter sa fonction dans l'interface
d'administration.
"""

from django.apps import AppConfig


class ContactConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contact"
    verbose_name = "Messages de contact"