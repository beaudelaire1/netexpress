"""
Project level URL configuration.

Routes requests to the appropriate application.  The landing page is served
by the ``core`` app, while services, quotation requests, and invoices are
handled by their respective apps.  Static and media files are only served by
Django when ``DEBUG`` is True.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

sitemaps = {"static": StaticViewSitemap}

urlpatterns = [
    # Expose the admin under a custom path as defined in the cahier des charges
    path("gestion/", admin.site.urls),

    # Public URLs (accessible to all)
    path("", include("core.urls")),
    path("services/", include("services.urls")),
    path("devis/", include("devis.urls")),
    path("factures/", include("factures.urls")),
    path("contact/", include("contact.urls")),
    
    # Authentication URLs
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("accounts/", include("django.contrib.auth.urls")),
    
    # Portal-specific URL patterns
    # Client Portal (/client/...)
    path("client/", include("core.urls_client")),
    path("client/messages/", include(("messaging.urls", "messaging"), namespace="client_messaging")),
    
    # Worker Portal (/worker/...)
    path("worker/", include(("core.urls_worker", "worker_portal"), namespace="worker")),
    path("worker/messages/", include(("messaging.urls", "messaging"), namespace="worker_messaging")),
    
    # Admin Portal (/admin-dashboard/...)
    path("admin-dashboard/", include("core.urls_admin")),
    path("admin-dashboard/messages/", include(("messaging.urls", "messaging"), namespace="admin_messaging")),
    
    # Legacy URLs (for backward compatibility)
    path("taches/", include("tasks.urls")),
    path("messages/", include(("messaging.urls", "messaging"), namespace="messaging")),
    
    # CKEditor URLs for WYSIWYG functionality
    path("ckeditor/", include("ckeditor_uploader.urls")),
    
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
