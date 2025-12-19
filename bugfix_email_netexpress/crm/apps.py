from django.apps import AppConfig


class CrmConfig(AppConfig):
    """Configuration for the CRM app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
    verbose_name = "CRM"