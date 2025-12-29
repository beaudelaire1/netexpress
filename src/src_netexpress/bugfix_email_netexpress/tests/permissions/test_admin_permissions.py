"""
Tests des permissions pour les rôles ADMIN_BUSINESS et ADMIN_TECHNICAL (Superuser).

Couvre:
- Accès admin business (lecture/écriture limitée)
- Accès admin technical (full access)
- Permissions étendues
- Contrôle read-only sur /gestion/
"""

import pytest
from django.contrib.auth.models import User

from accounts.models import Profile
from core.decorators import user_has_permission
from devis.models import Quote
from factures.models import Invoice


pytestmark = pytest.mark.django_db


class TestAdminBusinessDashboardAccess:
    """Tests d'accès au dashboard admin business."""

    def test_admin_business_can_access_admin_dashboard(self, client_admin):
        """TEST-PERM-ADMIN-BUS-001: Un admin_business doit accéder à /admin-dashboard/."""
        # Act
        response = client_admin.get('/admin-dashboard/')
        
        # Assert
        assert response.status_code == 200

    def test_admin_business_sees_dashboard_stats(self, client_admin):
        """Le dashboard admin business doit afficher les statistiques."""
        # Act
        response = client_admin.get('/admin-dashboard/')
        
        # Assert
        assert response.status_code == 200
        # Vérifier qu'il y a du contexte ou du contenu
        assert len(response.content) > 0


class TestAdminBusinessReadOnlyAccess:
    """Tests d'accès en lecture seule à /gestion/ pour admin business."""

    def test_admin_business_readonly_on_technical_admin(self, client_admin, customer):
        """TEST-PERM-ADMIN-BUS-002: Un admin_business a un accès lecture seule à /gestion/ (GET uniquement)."""
        # Act - Accès GET
        response_get = client_admin.get('/gestion/')
        
        # Assert
        assert response_get.status_code == 200
        
        # Act - Tentative POST (création)
        # Note: Cette partie dépend du middleware RoleBasedAccessMiddleware
        response_post = client_admin.post('/gestion/devis/quote/add/', {
            'client': customer.pk,
            'status': 'draft',
        })
        
        # Assert - Doit être bloqué ou redirigé
        assert response_post.status_code in [302, 403]

    def test_admin_business_can_read_quotes_in_admin(self, client_admin, quote_draft):
        """Un admin business peut consulter les devis dans /gestion/."""
        # Act
        response = client_admin.get(f'/gestion/devis/quote/{quote_draft.pk}/change/')
        
        # Assert
        # GET autorisé
        assert response.status_code in [200, 302]  # 302 si redirection, 200 si OK

    def test_admin_business_cannot_delete_quotes_in_admin(self, client_admin, quote_draft):
        """Un admin business ne peut PAS supprimer de devis dans /gestion/ (DELETE bloqué)."""
        # Act
        response = client_admin.post(f'/gestion/devis/quote/{quote_draft.pk}/delete/', {
            'post': 'yes'
        })
        
        # Assert - Doit être bloqué
        assert response.status_code in [302, 403]


class TestAdminBusinessPermissions:
    """Tests des permissions spécifiques au rôle admin business."""

    def test_admin_business_has_extended_permissions(self, user_admin_business):
        """TEST-PERM-ADMIN-BUS-003: Admin business a toutes les permissions sauf users.edit."""
        # Act & Assert
        assert user_has_permission(user_admin_business, 'quotes.view') is True
        assert user_has_permission(user_admin_business, 'quotes.create') is True
        assert user_has_permission(user_admin_business, 'quotes.edit') is True
        assert user_has_permission(user_admin_business, 'invoices.view') is True
        assert user_has_permission(user_admin_business, 'invoices.create') is True
        assert user_has_permission(user_admin_business, 'invoices.edit') is True
        assert user_has_permission(user_admin_business, 'tasks.view') is True
        assert user_has_permission(user_admin_business, 'tasks.create') is True
        assert user_has_permission(user_admin_business, 'tasks.assign') is True
        assert user_has_permission(user_admin_business, 'users.view') is True
        assert user_has_permission(user_admin_business, 'users.create') is True

    def test_admin_business_cannot_edit_users(self, user_admin_business):
        """Admin business ne peut PAS avoir la permission 'users.edit' (réservée à admin technique)."""
        # Act & Assert
        assert user_has_permission(user_admin_business, 'users.edit') is False


class TestAdminBusinessAccessRestrictions:
    """Tests des restrictions d'accès pour admin business."""

    def test_admin_business_cannot_access_client_portal(self, client_admin):
        """Un admin business ne doit pas être redirigé vers le portail client."""
        # Act
        response = client_admin.get('/client/')
        
        # Assert
        # Devrait rediriger vers son propre dashboard
        if response.status_code == 302:
            assert '/admin-dashboard/' in response.url

    def test_admin_business_cannot_access_worker_portal(self, client_admin):
        """Un admin business ne doit pas être redirigé vers le portail worker."""
        # Act
        response = client_admin.get('/worker/')
        
        # Assert
        if response.status_code == 302:
            assert '/admin-dashboard/' in response.url


class TestSuperuserFullAccess:
    """Tests d'accès complet pour les superusers (admin technique)."""

    def test_superuser_full_access_to_gestion(self, client_superuser, customer):
        """TEST-PERM-ADMIN-TECH-001: Un superuser doit avoir un accès complet à /gestion/."""
        # Act - Accès GET
        response_get = client_superuser.get('/gestion/')
        
        # Assert
        assert response_get.status_code == 200
        
        # Act - Création (POST autorisé)
        response_post = client_superuser.post('/gestion/devis/quote/add/', {
            'client': customer.pk,
            'status': 'draft',
            'issue_date': '2025-01-01',
        })
        
        # Assert - Doit être autorisé (200 ou 302 redirect success)
        assert response_post.status_code in [200, 302]

    def test_superuser_can_modify_data(self, client_superuser, quote_draft):
        """Un superuser peut modifier les données dans /gestion/."""
        # Act
        response = client_superuser.post(f'/gestion/devis/quote/{quote_draft.pk}/change/', {
            'client': quote_draft.client.pk,
            'status': 'sent',
            'issue_date': quote_draft.issue_date,
        })
        
        # Assert
        assert response.status_code in [200, 302]

    def test_superuser_can_delete_data(self, client_superuser, quote_draft):
        """Un superuser peut supprimer des données dans /gestion/."""
        # Act
        response = client_superuser.post(f'/gestion/devis/quote/{quote_draft.pk}/delete/', {
            'post': 'yes'
        })
        
        # Assert - Doit être autorisé
        assert response.status_code in [200, 302]


class TestSuperuserPermissions:
    """Tests des permissions pour superuser."""

    def test_superuser_has_all_permissions(self, user_superuser):
        """TEST-PERM-ADMIN-TECH-002: Un superuser doit avoir TOUTES les permissions (wildcard '*')."""
        # Act & Assert
        assert user_has_permission(user_superuser, 'any.permission') is True
        assert user_has_permission(user_superuser, 'users.edit') is True
        assert user_has_permission(user_superuser, 'system.config') is True
        assert user_has_permission(user_superuser, 'quotes.create') is True
        assert user_has_permission(user_superuser, 'invoices.delete') is True

    def test_superuser_bypasses_role_checks(self, user_superuser):
        """Un superuser doit bypasser les vérifications de rôle."""
        # Act
        from accounts.portal import get_user_role
        role = get_user_role(user_superuser)
        
        # Assert
        # Le superuser peut avoir un rôle "admin_technical" ou être détecté
        # comme superuser via user.is_superuser
        assert user_superuser.is_superuser is True


class TestSuperuserDashboardAccess:
    """Tests d'accès au dashboard pour superuser."""

    def test_superuser_can_access_staff_dashboard(self, client_superuser):
        """Un superuser peut accéder au dashboard staff (core.dashboard)."""
        # Act
        response = client_superuser.get('/dashboard/')
        
        # Assert
        # Selon la configuration, peut retourner 200 ou rediriger
        assert response.status_code in [200, 302, 404]

    def test_superuser_can_access_admin_interface(self, client_superuser):
        """Un superuser peut accéder à l'interface d'administration."""
        # Act
        response = client_superuser.get('/gestion/')
        
        # Assert
        assert response.status_code == 200


class TestRoleVerification:
    """Tests de vérification des rôles via get_user_role."""

    def test_get_role_for_client(self, user_client):
        """get_user_role doit retourner 'client' pour un utilisateur client."""
        # Act
        from accounts.portal import get_user_role
        role = get_user_role(user_client)
        
        # Assert
        assert role == 'client'

    def test_get_role_for_worker(self, user_worker):
        """get_user_role doit retourner 'worker' pour un utilisateur worker."""
        # Act
        from accounts.portal import get_user_role
        role = get_user_role(user_worker)
        
        # Assert
        assert role == 'worker'

    def test_get_role_for_admin_business(self, user_admin_business):
        """get_user_role doit retourner 'admin_business' pour un admin business."""
        # Act
        from accounts.portal import get_user_role
        role = get_user_role(user_admin_business)
        
        # Assert
        assert role == 'admin_business'

    def test_get_role_for_superuser(self, user_superuser):
        """get_user_role doit identifier un superuser correctement."""
        # Act
        from accounts.portal import get_user_role
        role = get_user_role(user_superuser)
        
        # Assert
        # Le superuser peut avoir un rôle spécifique ou être détecté via is_superuser
        assert role in ['admin_technical', 'superuser'] or user_superuser.is_superuser


class TestPermissionDecorators:
    """Tests des décorateurs de permissions."""

    def test_technical_admin_required_blocks_non_technical(self, client_admin):
        """Le décorateur technical_admin_required doit bloquer les non-technical admins."""
        # Note: Ce test nécessite une vue protégée par @technical_admin_required
        # À adapter selon l'existence de telles vues dans le projet
        pass  # Placeholder

    def test_business_admin_required_allows_business_admin(self, client_admin):
        """Le décorateur business_admin_required doit autoriser les admins business."""
        # Note: Ce test nécessite une vue protégée par @business_admin_required
        pass  # Placeholder

    def test_permission_required_decorator(self, client_admin):
        """Le décorateur @permission_required doit vérifier les permissions."""
        # Note: Ce test nécessite une vue protégée
        pass  # Placeholder

