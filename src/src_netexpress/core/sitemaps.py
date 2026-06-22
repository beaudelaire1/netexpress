"""Sitemaps du site public (SEO).

Expose un ``StaticViewSitemap`` pour les pages fixes et un
``ServiceSitemap`` pour les fiches de service actives.
"""

from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from services.models import Service


class StaticViewSitemap(Sitemap):
    """Pages statiques principales du site public."""

    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self) -> list[str]:
        return [
            "core:home",
            "core:about",
            "core:excellence",
            "core:realisations",
            "services:list",
            "contact:contact",
            "devis:request_quote",
            "core:mentions_legales",
            "core:confidentialite",
        ]

    def location(self, item: str) -> str:
        return reverse(item)


class ServiceSitemap(Sitemap):
    """Fiches de service actives."""

    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return Service.objects.filter(is_active=True)

    def location(self, obj: Service) -> str:
        return obj.get_absolute_url()


sitemaps = {
    "static": StaticViewSitemap,
    "services": ServiceSitemap,
}
