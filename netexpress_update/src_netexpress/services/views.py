"""
Vues en classes pour le catalogue des services.
Compatibles avec services/urls.py :
 - ServiceListView
 - ServiceDetailView
"""

from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404

from .models import Service, Category


class ServiceListView(ListView):
    model = Service
    template_name = "services/service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        qs = Service.objects.filter(is_active=True).order_by("title")
        category_slug = self.request.GET.get("category")
        if category_slug:
            self.category = get_object_or_404(Category, slug=category_slug)
            qs = qs.filter(category=self.category)
        else:
            self.category = None
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all().order_by("name")
        context["active_category"] = getattr(self, "category", None)
        return context


class ServiceDetailView(DetailView):
    model = Service
    template_name = "services/service_detail.html"
    context_object_name = "service"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Service.objects.filter(is_active=True)
