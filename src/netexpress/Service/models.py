"""
Modèles pour le catalogue historique des services.

Cette version de ``Service`` est conservée pour assurer une compatibilité
avec d’anciens projets mais bénéficie de la même refonte que l’app
``services`` en 2025 : les champs sont documentés, la méthode
``get_absolute_url`` est ajoutée pour obtenir des liens conviviaux et
les images sont facultatives.  Lorsqu’aucune image n’est fournie, les
templates utilisent désormais des photographies libres de droits
provenant d’Unsplash via des requêtes dynamiques (voir le fichier
template pour plus de détails)【668280112401708†L16-L63】.
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

    def get_absolute_url(self) -> str:
        """
        Retourne l'URL détaillée pour ce service.

        Cette méthode est utilisée dans les templates et l'administration
        pour générer des liens pointant vers ``services:detail``.  Elle est
        ajoutée ici afin d'offrir la même interface que l'app moderne
        ``services`` et de faciliter les redirections.
        """
        from django.urls import reverse
        return reverse("services:detail", args=[self.slug])