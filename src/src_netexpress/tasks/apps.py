from django.apps import AppConfig


class TasksConfig(AppConfig):
    """Configuration de l'application de suivi des tâches."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tasks"
    verbose_name = "suivi des tâches"

    def ready(self) -> None:
        """Enregistre les signaux et laisse Django exposer toute erreur d'import."""
        from . import signals  # noqa: F401
