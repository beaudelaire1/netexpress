"""
URL routing for the invoices application.

Only staff should access these URLs.  They allow creating a new invoice
from a quote and downloading an existing invoice's PDF file.
"""

from django.urls import path
from . import views

app_name = "invoices"

urlpatterns = [
    path("create/<int:quote_id>/", views.create_invoice, name="create"),
    path("download/<int:pk>/", views.download_invoice, name="download"),
]