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

  En 2025, ces modèles ont été étendus avec la méthode ``get_absolute_url``
  qui simplifie l'obtention d'URL canoniques depuis les templates.
  De plus, les gabarits utilisent désormais des images locales comme
  solutions de repli lorsque aucune image n'est fournie en base de
  données.  Toute dépendance à des services externes (e.g. Unsplash) a été
  retirée【668280112401708†L16-L63】.
"""

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


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
        verbose_name = _("catégorie")
        verbose_name_plural = _("catégories")


    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        """
        Override save to automatically generate a unique slug based on the
        category name.  If a slug already exists, append a numeric suffix
        (e.g. ``nettoyage``, ``nettoyage-1``, ``nettoyage-2``, …).  When
        editing an existing category (i.e. `self.pk` is set), the slug
        generation only runs if the name has changed or the slug is empty.

        Parameters
        ----------
        *args, **kwargs
            Forwarded to the parent save implementation.
        """
        _slugify = slugify
        generate = False
        # If no slug or slug manually cleared, generate a new one
        if not self.slug:
            generate = True
        elif self.pk and self.name:
            # Fetch the current record from DB to detect name changes
            try:
                current = Category.objects.get(pk=self.pk)
                if current.name != self.name:
                    generate = True
            except Category.DoesNotExist:
                generate = True
        if generate and self.name:
            base_slug = _slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            # Ensure the slug is unique.  Exclude the current record when updating.
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        """
        Retourne l'URL vers la liste des services filtrée par cette catégorie.

        Cette méthode fournit un point d'entrée convivial pour les gabarits et
        autres composants afin de générer un lien direct vers les services
        appartenant à cette catégorie.  L'URL retournée utilise le nom de
        l'espace de noms de l'application ``services`` et ajoute un paramètre
        de requête ``category`` basé sur le slug de l'objet.  Par exemple :

        >>> from django.urls import reverse
        >>> cat = Category(slug="nettoyage", name="Nettoyage")
        >>> url = cat.get_absolute_url()  # doctest: +SKIP
        >>> url.endswith('?category=nettoyage')
        True
        """
        base_url = reverse("services:list")
        return f"{base_url}?category={self.slug}"


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
    unit_type = models.CharField(
        _("Unité de mesure"),
        max_length=50,
        help_text=_("Type d'unité pour la saisie (ex. m², heure, forfait)."),
        default="forfait",
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
        return reverse("services:detail", kwargs={"slug": self.slug})

    class Meta:
        ordering = ["title"]
        verbose_name = _("service")
        verbose_name_plural = _("services")
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        """
        Override save to automatically generate a unique slug based on the
        service title.  When adding a new service or when the title has
        changed, the slug is generated using ``slugify`` and suffixed with
        ``-1``, ``-2``, … until it is unique.  This prevents ``IntegrityError``
        exceptions when titles differ only by punctuation or case.  When
        editing an existing service, the slug remains unchanged unless the
        title has been modified or the slug is empty.

        Parameters
        ----------
        *args, **kwargs
            Forwarded to the parent save implementation.
        """
        _slugify = slugify
        generate = False
        # Determine if we need to generate a slug
        if not self.slug:
            generate = True
        elif self.pk:
            try:
                current = Service.objects.get(pk=self.pk)
                if current.title != self.title:
                    generate = True
            except Service.DoesNotExist:
                generate = True
        if generate and self.title:
            base_slug = _slugify(self.title, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Service.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ServiceTask(models.Model):
    """Checklist item associated with a service."""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("tâche")
        verbose_name_plural = _("tâches")

    def __str__(self) -> str:
        return self.name