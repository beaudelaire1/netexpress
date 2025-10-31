"""
URL routing for the quotes application.

This app uses a namespace of ``quotes`` to allow reversing its URLs unambiguously.
"""

from django.urls import path
from . import views

app_name = "quotes"

urlpatterns = [
    path("", views.request_quote, name="request_quote"),
    path("merci/", views.quote_success, name="quote_success"),
]