from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return ["core:home", "services:list", "core:excellence", "core:realisations", "contact:contact", "devis:request_quote"]

    def location(self, item):
        return reverse(item)
