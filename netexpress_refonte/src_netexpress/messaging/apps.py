from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """Configuration de l'application messagerie.

    Cette application fournit un modèle de message e‑mail générique,
    un service pour envoyer des messages et des vues pour les
    consulter.  Elle est enregistrée sous le label ``messaging``.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "messaging"
    verbose_name = "messagerie"