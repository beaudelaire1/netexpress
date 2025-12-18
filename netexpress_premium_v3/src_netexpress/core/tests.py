"""
Tests unitaires basiques pour l’app ``core``.  Ces tests servent
principalement d’exemple et peuvent être enrichis pour vérifier le
rendu des pages statiques d’accueil ou d’à propos.
"""

from django.test import TestCase
from django.urls import reverse


class CoreViewsTests(TestCase):
    """Vérifie que les pages principales se chargent correctement."""

    def test_home_page(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_about_page(self):
        response = self.client.get(reverse("core:about"))
        self.assertEqual(response.status_code, 200)