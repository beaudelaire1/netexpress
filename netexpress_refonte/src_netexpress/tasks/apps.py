from django.apps import AppConfig


class TasksConfig(AppConfig):
    """Configuration for the ``tasks`` application.

    This class registers signal handlers that send notifications when
    tasks are saved.  It is referenced from the project's settings when
    the application is included in ``INSTALLED_APPS``.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "tasks"
    verbose_name = "suivi des tâches"

    def ready(self) -> None:
        # Import signal handlers so that they are registered as soon as
        # Django starts.  The import is done lazily to avoid issues
        # during migrations.
        try:
            from . import signals  # noqa: F401
        except Exception:
            # During migrations or if dependencies are missing the import
            # may fail; ignore such errors to avoid breaking startup.
            pass
