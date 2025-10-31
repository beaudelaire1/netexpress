"""
Project level URL configuration.

Routes requests to the appropriate application.  The landing page is served
by the ``core`` app, while services, quotation requests, and invoices are
handled by their respective apps.  Static and media files are only served by
Django when ``DEBUG`` is True.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("services/", include("Service.urls")),
    path("devis/", include("quotes.urls")),
    path("factures/", include("invoices.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
