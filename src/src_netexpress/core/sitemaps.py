from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """
    Sitemap pour les pages statiques principales du site.
    Optimisé pour le SEO local en Guyane française.
    """
    changefreq = "weekly"
    protocol = 'https'

    # Priorités et fréquences de mise à jour par page
    _priority_map = {
        "core:home": 1.0,           # Page d'accueil - priorité maximale
        "services:list": 0.9,       # Catalogue des services
        "devis:request_quote": 0.9, # Formulaire de devis
        "contact:contact": 0.8,     # Page de contact
        "core:excellence": 0.7,     # Engagement qualité
        "core:realisations": 0.7,   # Galerie des réalisations
    }

    _changefreq_map = {
        "core:home": "daily",
        "services:list": "weekly",
        "devis:request_quote": "monthly",
        "contact:contact": "monthly",
        "core:excellence": "monthly",
        "core:realisations": "weekly",
    }

    def items(self):
        return [
            "core:home",
            "services:list",
            "devis:request_quote",
            "contact:contact",
            "core:excellence",
            "core:realisations",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self._priority_map.get(item, 0.5)

    def changefreq(self, item):
        return self._changefreq_map.get(item, "monthly")
