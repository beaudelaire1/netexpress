"""
Tests unitaires basiques pour l’app ``core``.  Ces tests servent
principalement d’exemple et peuvent être enrichis pour vérifier le
rendu des pages statiques d’accueil ou d’à propos.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class CoreViewsTests(TestCase):
    """Vérifie que les pages principales se chargent correctement."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_home',
            email='admin-home@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )

    def test_home_page(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_home_page_dashboard_link_targets_admin_dashboard_for_superuser(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/admin-dashboard/"')
        self.assertNotContains(response, 'href="/gestion/"')

    def test_about_page(self):
        response = self.client.get(reverse("core:about"))
        self.assertEqual(response.status_code, 200)