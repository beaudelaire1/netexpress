from django.conf import settings
from django.db import models


class Customer(models.Model):
    """
    Centralised customer model used across the ERP.

    A customer may optionally be linked to a Django user account via
    ``user``.  This association makes it possible to authenticate
    customers on the platform (for example, when they access their
    dashboard).  When not linked to a user, the customer record simply
    stores contact and address information.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profile",
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "client"
        verbose_name_plural = "clients"
        # Use the same database table as the legacy ``devis.Client`` model.
        # This ensures that existing rows remain valid and no foreign key
        # integrity errors occur when migrating from previous versions.
        db_table = "devis_client"

    def __str__(self) -> str:
        return self.full_name
