"""Tests pour les templates et vues de services.

Ce module teste que les templates et vues de services gèrent correctement
les cas où les données peuvent être manquantes (catégories, images, etc.).
"""

import pytest
from django.test import Client
from django.urls import reverse

from services.models import Service, Category


pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    """Crée une catégorie de test."""
    return Category.objects.create(
        name="Nettoyage",
        slug="nettoyage"
    )


@pytest.fixture
def service_with_category(category):
    """Crée un service avec une catégorie."""
    return Service.objects.create(
        title="Service de nettoyage complet",
        category=category,
        description="Description du service de nettoyage",
        duration_minutes=120,
        is_active=True
    )


@pytest.fixture
def service_without_category():
    """
    Crée un service sans catégorie (cas théorique).
    
    Note: En pratique, cela ne devrait pas arriver car category est un
    ForeignKey obligatoire, mais on peut tester le comportement du template
    si la catégorie est supprimée après coup.
    """
    # On doit d'abord créer avec une catégorie, puis la supprimer
    cat = Category.objects.create(name="Temp", slug="temp")
    service = Service.objects.create(
        title="Service sans catégorie",
        category=cat,
        description="Description du service",
        duration_minutes=60,
        is_active=True
    )
    # On simule une suppression en mettant à None (si possible)
    # Dans la pratique, avec CASCADE, le service serait supprimé
    return service


class TestServiceListView:
    """Tests pour la vue liste des services."""

    def test_service_list_renders_successfully(self, client, service_with_category):
        """La page liste des services doit s'afficher sans erreur 500."""
        response = client.get(reverse('services:list'))
        assert response.status_code == 200
        assert 'services' in response.context

    def test_service_list_shows_active_services(self, client, service_with_category):
        """La liste doit afficher les services actifs."""
        response = client.get(reverse('services:list'))
        assert service_with_category in response.context['services']

    def test_service_list_hides_inactive_services(self, client, service_with_category):
        """La liste ne doit pas afficher les services inactifs."""
        service_with_category.is_active = False
        service_with_category.save()
        
        response = client.get(reverse('services:list'))
        assert service_with_category not in response.context['services']

    def test_service_list_filters_by_category(self, client, service_with_category, category):
        """La liste peut être filtrée par catégorie."""
        response = client.get(reverse('services:list') + f'?category={category.slug}')
        assert response.status_code == 200
        assert service_with_category in response.context['services']


class TestServiceDetailView:
    """Tests pour la vue détail d'un service."""

    def test_service_detail_renders_successfully(self, client, service_with_category):
        """La page détail d'un service doit s'afficher sans erreur 500."""
        response = client.get(
            reverse('services:detail', kwargs={'slug': service_with_category.slug})
        )
        assert response.status_code == 200
        assert response.context['service'] == service_with_category

    def test_service_detail_shows_category_when_present(self, client, service_with_category):
        """Le détail doit afficher la catégorie si elle existe."""
        response = client.get(
            reverse('services:detail', kwargs={'slug': service_with_category.slug})
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert service_with_category.category.name in content

    def test_service_detail_handles_missing_image(self, client, service_with_category):
        """Le détail doit gérer l'absence d'image."""
        # Le service n'a pas d'image par défaut
        assert not service_with_category.image
        
        response = client.get(
            reverse('services:detail', kwargs={'slug': service_with_category.slug})
        )
        assert response.status_code == 200
        # Le template devrait afficher une image par défaut

    def test_service_detail_shows_duration(self, client, service_with_category):
        """Le détail doit afficher la durée estimée."""
        response = client.get(
            reverse('services:detail', kwargs={'slug': service_with_category.slug})
        )
        assert response.status_code == 200
        content = response.content.decode()
        # On vérifie que la durée est affichée
        assert str(service_with_category.duration_minutes) in content

    def test_service_detail_does_not_show_base_price(self, client, service_with_category):
        """Le détail ne doit pas référencer base_price qui n'existe pas."""
        response = client.get(
            reverse('services:detail', kwargs={'slug': service_with_category.slug})
        )
        assert response.status_code == 200
        content = response.content.decode()
        # On vérifie que base_price n'est pas dans le template
        assert 'base_price' not in content.lower()

    def test_inactive_service_not_accessible(self, client, service_with_category):
        """Un service inactif ne devrait pas être accessible."""
        service_with_category.is_active = False
        service_with_category.save()
        
        response = client.get(
            reverse('services:detail', kwargs={'slug': service_with_category.slug})
        )
        assert response.status_code == 404


class TestServiceTemplateRobustness:
    """Tests pour la robustesse des templates."""

    def test_service_list_template_handles_empty_category(self, client):
        """Le template de liste gère les catégories vides."""
        response = client.get(reverse('services:list'))
        assert response.status_code == 200
        # Aucune erreur même sans services ni catégories

    def test_service_detail_template_with_empty_description(self, client, category):
        """Le template de détail gère les descriptions vides."""
        service = Service.objects.create(
            title="Service sans description",
            category=category,
            description="",  # Description vide
            duration_minutes=60,
            is_active=True
        )
        
        response = client.get(
            reverse('services:detail', kwargs={'slug': service.slug})
        )
        assert response.status_code == 200
