from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return [
            "core:home",
            "services:list",
            "core:excellence",
            "core:realisations",
            "contact:contact",
            "devis:request_quote",
            "core:legal_notice",
            "core:privacy_policy",
        ]

    def location(self, item):
        return reverse(item)


class ServiceSitemap(Sitemap):
    """Fiches de service dynamiques (auparavant absentes du sitemap)."""

    priority = 0.6
    changefreq = "weekly"

    def items(self):
        from services.models import Service

        return Service.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_absolute_url()
