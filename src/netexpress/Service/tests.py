from django.test import TestCase

"""
Batterie de tests minimaliste pour l'app ``Service``.

Cette app est conservée à des fins de compatibilité et n’inclut pas
d’implémentation métier supplémentaire.  Les tests devraient vérifier
que la méthode ``get_absolute_url`` fonctionne correctement et que les
slugs sont générés à partir du titre.  Vous pouvez étendre cette
classe avec des tests unitaires ou d'intégration selon vos besoins.
"""

from django.test import TestCase
from .models import Service


class ServiceModelTests(TestCase):
    """Tests simples pour le modèle Service hérité."""

    def test_slug_is_generated_on_save(self):
        service = Service.objects.create(
            title="Test Service",
            description="Desc",
            short_description="Short",
            base_price=10,
            duration_minutes=30,
            slug="",
        )
        self.assertTrue(service.slug.startswith("test-service"))

    def test_get_absolute_url(self):
        service = Service.objects.create(
            title="Another",
            description="",
            short_description="",
            base_price=5,
            duration_minutes=15,
        )
        # Should return a string like '/services/<slug>/'
        self.assertIn(service.slug, service.get_absolute_url())
