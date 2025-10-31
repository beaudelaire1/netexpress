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
    # Expose the admin under a custom path as defined in the cahier des charges
    path("gestion/", admin.site.urls),

    path("", include("core.urls")),
    path("services/", include("services.urls")),
    path("devis/", include("devis.urls")),
    path("factures/", include("factures.urls")),
    path("contact/", include("contact.urls")),
    path("taches/", include("tasks.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
