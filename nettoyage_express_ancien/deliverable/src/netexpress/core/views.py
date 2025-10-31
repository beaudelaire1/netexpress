"""
Core application views.

The home view renders the landing page with a selection of featured services.
The health view is used by monitoring tools to verify the application is
responding properly.
"""

from django.shortcuts import render
from django.http import JsonResponse
from Service.models import Service


def home(request):
    """
    Render the landing page. A handful of active services are selected to be
    displayed as highlights.  Adjust the number of services shown here to
    customise the homepage.
    """
    featured = Service.objects.filter(is_active=True).order_by("title")[:6]
    return render(request, "home.html", {"featured_services": featured})


def health(request):
    """Simple JSON endpoint used by uptime probes to check application health."""
    return JsonResponse({"status": "ok"})