"""
URL definitions for the service catalogue.

This module wires up views that display a list of available services and
detailed pages for each individual service.  The URL namespace is
``services`` to avoid clashes with other apps.
"""

from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceListView.as_view(), name="list"),
    path("<slug:slug>/", views.ServiceDetailView.as_view(), name="detail"),
]