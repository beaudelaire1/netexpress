"""Tests pour les décorateurs personnalisés de NetExpress.

Ce module teste le comportement du décorateur business_admin_required qui
contrôle l'accès aux vues en fonction des permissions utilisateur.
"""

import pytest
from django.contrib.auth.models import User, Group
from django.test import RequestFactory
from django.http import HttpResponse

from core.decorators import business_admin_required, is_business_admin


pytestmark = pytest.mark.django_db


@pytest.fixture
def request_factory():
    """Factory pour créer des requêtes HTTP de test."""
    return RequestFactory()


@pytest.fixture
def admin_business_group():
    """Crée et retourne le groupe admin_business."""
    group, _ = Group.objects.get_or_create(name='admin_business')
    return group


@pytest.fixture
def staff_user():
    """Crée un utilisateur staff."""
    return User.objects.create_user(
        username='staff_user',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def business_admin_user(admin_business_group):
    """Crée un utilisateur membre du groupe admin_business."""
    user = User.objects.create_user(
        username='business_admin',
        password='testpass123',
        is_staff=False
    )
    user.groups.add(admin_business_group)
    return user


@pytest.fixture
def regular_user():
    """Crée un utilisateur régulier sans permissions spéciales."""
    return User.objects.create_user(
        username='regular_user',
        password='testpass123',
        is_staff=False
    )


class TestIsBusinessAdmin:
    """Tests pour la fonction is_business_admin."""

    def test_staff_user_is_business_admin(self, staff_user):
        """Un utilisateur staff doit être considéré comme business admin."""
        assert is_business_admin(staff_user) is True

    def test_admin_business_group_user_is_business_admin(self, business_admin_user):
        """Un utilisateur du groupe admin_business doit être considéré comme business admin."""
        assert is_business_admin(business_admin_user) is True

    def test_regular_user_is_not_business_admin(self, regular_user):
        """Un utilisateur régulier ne doit pas être considéré comme business admin."""
        assert is_business_admin(regular_user) is False

    def test_unauthenticated_user_is_not_business_admin(self):
        """Un utilisateur non authentifié ne doit pas être considéré comme business admin."""
        from django.contrib.auth.models import AnonymousUser
        assert is_business_admin(AnonymousUser()) is False


class TestBusinessAdminRequiredDecorator:
    """Tests pour le décorateur business_admin_required."""

    def test_staff_user_can_access_view(self, request_factory, staff_user):
        """Un utilisateur staff doit pouvoir accéder à une vue protégée."""
        @business_admin_required
        def protected_view(request):
            return HttpResponse("Success")

        request = request_factory.get('/test/')
        request.user = staff_user
        response = protected_view(request)
        assert response.status_code == 200
        assert response.content == b"Success"

    def test_business_admin_user_can_access_view(self, request_factory, business_admin_user):
        """Un utilisateur du groupe admin_business doit pouvoir accéder à une vue protégée."""
        @business_admin_required
        def protected_view(request):
            return HttpResponse("Success")

        request = request_factory.get('/test/')
        request.user = business_admin_user
        response = protected_view(request)
        assert response.status_code == 200
        assert response.content == b"Success"

    def test_regular_user_redirected_to_login(self, request_factory, regular_user):
        """Un utilisateur régulier doit être redirigé vers la page de login."""
        @business_admin_required
        def protected_view(request):
            return HttpResponse("Success")

        request = request_factory.get('/test/')
        request.user = regular_user
        response = protected_view(request)
        assert response.status_code == 302
        assert '/admin/login/' in response.url

    def test_anonymous_user_redirected_to_login(self, request_factory):
        """Un utilisateur anonyme doit être redirigé vers la page de login."""
        from django.contrib.auth.models import AnonymousUser
        
        @business_admin_required
        def protected_view(request):
            return HttpResponse("Success")

        request = request_factory.get('/test/')
        request.user = AnonymousUser()
        response = protected_view(request)
        assert response.status_code == 302
        assert '/admin/login/' in response.url


class TestFacturesViewsAccess:
    """Tests d'intégration pour vérifier l'accès aux vues de factures."""

    def test_staff_can_access_archive(self, client, staff_user):
        """Un utilisateur staff peut accéder à la page d'archive des factures."""
        client.force_login(staff_user)
        response = client.get('/factures/archive/')
        # On vérifie que l'utilisateur n'est pas redirigé vers le login
        assert response.status_code != 302 or '/admin/login/' not in response.url

    def test_business_admin_can_access_archive(self, client, business_admin_user):
        """Un utilisateur admin_business peut accéder à la page d'archive des factures."""
        client.force_login(business_admin_user)
        response = client.get('/factures/archive/')
        # On vérifie que l'utilisateur n'est pas redirigé vers le login
        assert response.status_code != 302 or '/admin/login/' not in response.url

    def test_regular_user_cannot_access_archive(self, client, regular_user):
        """Un utilisateur régulier ne peut pas accéder à la page d'archive des factures."""
        client.force_login(regular_user)
        response = client.get('/factures/archive/')
        # L'utilisateur doit être redirigé
        assert response.status_code == 302
        assert '/admin/login/' in response.url

    def test_anonymous_cannot_access_archive(self, client):
        """Un utilisateur anonyme ne peut pas accéder à la page d'archive des factures."""
        response = client.get('/factures/archive/')
        # L'utilisateur doit être redirigé
        assert response.status_code == 302
        assert '/admin/login/' in response.url
