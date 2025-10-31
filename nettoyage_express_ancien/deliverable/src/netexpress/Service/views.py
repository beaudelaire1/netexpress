"""
Views for displaying services.

The list view shows all active services, and the detail view presents
comprehensive information about a single service. Both use generic class-based
views for brevity and customisation via templates.
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
