"""
Vues pour l’affichage du catalogue de services hérité.

Les vues de liste et de détail sont basées sur des classes génériques
Django pour plus de concision.  Elles filtrent uniquement les services
actifs et délèguent le rendu aux templates de l’app moderne
``services``.  Les pages détaillées utilisent des images importées
d’Unsplash lorsque nécessaire, afin de garantir un rendu esthétique même
lorsqu’aucune photo n’est fournie【668280112401708†L16-L63】.
"""

from django.views.generic import ListView, DetailView
from .models import Service


class ServiceListView(ListView):
    model = Service
    template_name = "services/service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        """
        Only return services marked as active.  This allows administrators to
        deactivate services without deleting them.
        """
        return Service.objects.filter(is_active=True)


class ServiceDetailView(DetailView):
    model = Service
    template_name = "services/service_detail.html"
    context_object_name = "service"
