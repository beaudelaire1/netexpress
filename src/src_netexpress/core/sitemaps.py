from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    """Sitemap for static pages with variable priorities."""
    
    def items(self):
        # Return tuples of (url_name, priority, changefreq)
        return [
            ("core:home", 1.0, "daily"),
            ("services:list", 0.9, "weekly"),
            ("devis:request_quote", 0.9, "weekly"),
            ("contact:contact", 0.8, "monthly"),
            ("core:excellence", 0.7, "monthly"),
            ("core:realisations", 0.7, "monthly"),
        ]
    
    def location(self, item):
        return reverse(item[0])
    
    def priority(self, item):
        return item[1]
    
    def changefreq(self, item):
        return item[2]


class ServiceSitemap(Sitemap):
    """Sitemap for service pages."""
    changefreq = "weekly"
    priority = 0.8
    
    def items(self):
        from services.models import Service
        return Service.objects.filter(is_active=True)
    
    def lastmod(self, obj):
        return obj.created_at
