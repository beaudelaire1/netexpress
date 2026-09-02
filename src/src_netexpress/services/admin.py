"""
Configuration de l’administration pour les services et leurs tâches.

Ce module définit la manière dont les services et les tâches associées
s’affichent dans l’interface d’administration.  En 2025, nous avons
    modernisé la présentation : les illustrations des services peuvent
    être absentes, auquel cas des images locales (dossier ``static/img``)
    sont utilisées dans les pages publiques.  Cette configuration permet
    d’éditer les tâches directement en ligne pour faciliter la gestion des
    checklists.  Jazzmin, s’il est installé, se chargera de l’esthétique;
    sinon, le thème par défaut reste propre et fonctionnel.
"""

from django import forms
from django.contrib import admin
from django.db.models import Count

from .models import Category, Service, ServiceTask


class ServiceTaskInline(admin.TabularInline):
    model = ServiceTask
    extra = 1


class ServiceAdminForm(forms.ModelForm):
    """Formulaire d'administration des services.

    Rend le texte alternatif (``image_alt``) obligatoire dans l'interface
    d'administration afin de garantir que chaque service publié dispose d'une
    description d'image accessible et optimisée pour le référencement, tout en
    conservant un champ non contraignant au niveau de la base de données pour
    les enregistrements historiques.
    """

    class Meta:
        model = Service
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "image_alt" in self.fields:
            self.fields["image_alt"].required = True


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    form = ServiceAdminForm
    # is_active est modifiable depuis la liste : retirer une prestation du site
    # le temps d'une saison ne doit pas obliger à ouvrir sa fiche. Le champ ne
    # peut pas être en première colonne, celle-ci portant le lien d'édition.
    list_display = ("title", "category", "unit_type", "nombre_de_taches", "is_active")
    list_editable = ("is_active",)
    list_filter = ("is_active", "category")
    list_per_page = 40
    search_fields = ("title", "description", "short_description", "image_alt")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ServiceTaskInline]
    actions = ("activer", "desactiver")

    def get_queryset(self, request):
        # Sans cette annotation, afficher le nombre de tâches déclencherait une
        # requête par ligne.
        return super().get_queryset(request).select_related("category").annotate(
            _nombre_de_taches=Count("tasks")
        )

    @admin.display(description="Tâches", ordering="_nombre_de_taches")
    def nombre_de_taches(self, obj) -> int:
        return obj._nombre_de_taches

    @admin.action(description="Activer les prestations sélectionnées")
    def activer(self, request, queryset):
        modifiees = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{modifiees} prestation(s) activée(s) : elles réapparaissent sur le site.",
        )

    @admin.action(description="Désactiver les prestations sélectionnées")
    def desactiver(self, request, queryset):
        modifiees = queryset.update(is_active=False)
        # Rien n'est supprimé : les devis déjà établis conservent leur contenu,
        # seules la liste publique et la fiche cessent de proposer la prestation.
        self.message_user(
            request,
            f"{modifiees} prestation(s) désactivée(s) : elles disparaissent du site, "
            "sans effet sur les devis existants.",
        )

# Register Category so administrators can manage top‑level categories.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    # Inclure l'icône dans le formulaire afin de pouvoir téléverser une image.
    fields = ("name", "slug", "icon")