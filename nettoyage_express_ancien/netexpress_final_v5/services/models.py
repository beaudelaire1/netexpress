"""
Modèles pour le catalogue des services.

Cette module définit les entités suivantes :

* ``Category`` : classification de haut niveau pour les services (espaces
  verts, nettoyage, peinture, bricolage).  Chaque catégorie possède un slug
  utilisé dans les URL, un nom lisible et une icône facultative.
* ``Service`` : description d'une prestation proposée par l'entreprise,
  incluant sa catégorie, ses informations tarifaires, un texte descriptif,
  une image d'illustration et un indicateur d'activation.  Un champ
  ``created_at`` trace la date de publication.
* ``ServiceTask`` : élément de checklist associé à un service (par exemple
  « Débroussaillage » ou « Taille de haies »).  Les tâches sont ordonnées
  et affichées sur la page de détail.

En 2025, ces modèles ont été étendus avec la méthode ``get_absolute_url``
qui simplifie l'obtention d'URL canoniques depuis les templates.  De plus,
les gabarits utilisent désormais des images libres de droits (Unsplash)
comme solutions de repli lorsque aucune image n'est fournie en base de
données【668280112401708†L16-L63】.
"""

from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """High‑level classification for services (e.g. espaces verts, nettoyage).

    The ``slug`` is used in URLs and filters, while ``name`` is displayed to
    end‑users.  An optional ``icon`` field can store the name of an icon or
    an SVG reference.  Categories are editable via the admin and used as
    foreign keys on ``Service`` objects.
    """

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    # Champ image pour l'icône.  Permet de téléverser un fichier depuis
    # l'interface d'administration (PNG, JPG, SVG).  Les fichiers sont
    # stockés dans le dossier ``media/categories``.  Un champ CharField
    # était initialement utilisé, ce qui empêchait l'upload d'images.
    icon = models.ImageField(
        upload_to="categories",
        blank=True,
        null=True,
        help_text="Icône de la catégorie (image téléversée)"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"

    def __str__(self) -> str:
        return self.name


class Service(models.Model):
    title = models.CharField(max_length=200, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="services",
        help_text="Catégorie du service"
    )
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
    created_at = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self) -> str:
        """
        Retourne l'URL canonique pour accéder à la fiche de ce service.

        L'utilisation de cette méthode permet d'améliorer la lisibilité du code
        dans les templates (``{{ service.get_absolute_url }}`` au lieu de
        construire manuellement l'URL).  L'URL est générée à partir du slug
        défini pour chaque service.
        """
        from django.urls import reverse
        return reverse("services:detail", kwargs={"slug": self.slug})

    class Meta:
        ordering = ["title"]
        verbose_name = "service"
        verbose_name_plural = "services"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        # Automatically generate slug on first save if not provided
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class ServiceTask(models.Model):
    """Checklist item associated with a service."""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "tâche"
        verbose_name_plural = "tâches"

    def __str__(self) -> str:
        return self.name