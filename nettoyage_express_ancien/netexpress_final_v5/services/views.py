"""
Vues pour le catalogue des services.

Cette module expose deux vues : une liste des services actifs et une fiche
détaillée pour un service individuel (avec la liste des tâches associées).  En
2025, le design a été amélioré et les vues intègrent désormais des images de
remplacement issues de Unsplash lorsqu'aucune image n'est fournie dans la base
de données.  Les vues restent basées sur les classes génériques de Django afin
de faciliter leur extension et leur personnalisation.
"""

from django.views.generic import ListView, DetailView

from .models import Service


class ServiceListView(ListView):
    model = Service
    template_name = "services/service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        """
        Return active services.  If a ``category`` query parameter is present,
        filter the queryset to only include services belonging to that
        category (matching on the slug).  This allows linking directly to
        category pages from the homepage.
        """
        qs = Service.objects.filter(is_active=True)
        cat_slug = self.request.GET.get("category")
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        return qs


class ServiceDetailView(DetailView):
    model = Service
    template_name = "services/service_detail.html"
    context_object_name = "service"