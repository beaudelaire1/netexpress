"""
Models for the service catalogue.

This module defines the core ``Service`` model used to store the company's
offerings, such as lawn care, cleaning, painting, or general handyman work.
Each service has a descriptive title, a detailed description, a base price,
an estimated duration, and an optional image for the marketing page.

Additionally, a slug field is generated from the title for human‑readable URLs.
"""

from django.db import models
from django.utils.text import slugify


class Service(models.Model):
    """Represents a service provided by the business."""

    title = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Description courte utilisée sur la page d'accueil."
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Prix de base en euros pour ce service."
    )
    duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Durée estimée en minutes pour exécuter ce service."
    )
    image = models.ImageField(
        upload_to="services",
        blank=True,
        null=True,
        help_text="Image illustrative du service."
    )
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text="Identifiant d'URL généré automatiquement."
    )

    class Meta:
        ordering = ["title"]
        verbose_name = "service"
        verbose_name_plural = "services"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        """
        Automatically derive the slug from the title when creating a new service.

        If a slug already exists, it will not be overwritten, allowing custom
        slugs to be assigned manually from the admin if desired.
        """
        if not self.slug:
            # slugify returns lowercase ASCII; allow unicode for accentuated words
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)