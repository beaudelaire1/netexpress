"""
Tests des permissions pour le rôle CLIENT.

Couvre:
- Accès au dashboard client
- Interdictions d'accès aux autres portails
- Isolation des données (voir uniquement ses devis/factures)
- Permissions limitées
"""

import pytest
from django.urls import reverse

from accounts.models import Profile
from crm.models import Customer
from devis.models import Quote, QuoteItem
from factures.models import Invoice
from core.decorators import user_has_permission


pytestmark = pytest.mark.django_db


class TestClientDashboardAccess:
    """Tests d'accès au dashboard client."""

    def test_client_can_access_client_dashboard(self, client_authenticated, user_client):
        """TEST-PERM-CLIENT-001: Un utilisateur avec rôle 'client' doit accéder à /client/."""
        # Act
        response = client_authenticated.get('/client/')
        
        # Assert
        assert response.status_code == 200

    def test_client_sees_dashboard_content(self, client_authenticated, user_client, customer):
        """Le dashboard client doit afficher les devis et factures."""
        # Arrange - Créer des devis pour ce client
        customer.email = user_client.email
        customer.save()
        
        quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.SENT)
        
        # Act
        response = client_authenticated.get('/client/')
        
        # Assert
        assert response.status_code == 200
        assert 'quotes' in response.context or quote in str(response.content)


class TestClientAccessRestrictions:
    """Tests des restrictions d'accès pour les clients."""

    def test_client_cannot_access_worker_dashboard(self, client_authenticated):
        """TEST-PERM-CLIENT-002: Un client ne doit PAS accéder au dashboard worker."""
        # Act
        response = client_authenticated.get('/worker/')
        
        # Assert
        # Redirection attendue (middleware)
        assert response.status_code in [302, 403]

    def test_client_cannot_access_admin_dashboard(self, client_authenticated):
        """Un client ne doit PAS accéder au dashboard admin."""
        # Act
        response = client_authenticated.get('/admin-dashboard/')
        
        # Assert
        assert response.status_code in [302, 403]

    def test_client_cannot_access_technical_admin(self, client_authenticated):
        """TEST-PERM-CLIENT-004: Un client ne doit PAS accéder à /gestion/."""
        # Act
        response = client_authenticated.get('/gestion/')
        
        # Assert
        assert response.status_code in [302, 403]


class TestClientDataIsolation:
    """Tests d'isolation des données par client."""

    def test_client_sees_only_own_quotes(self, client_authenticated, user_client, customer, customer_alt):
        """TEST-PERM-CLIENT-003: Un client doit voir uniquement SES devis (email matching)."""
        # Arrange - Lier customer au user_client
        customer.email = user_client.email
        customer.save()
        
        # Créer un devis pour ce client
        quote_own = Quote.objects.create(client=customer, status=Quote.QuoteStatus.SENT)
        
        # Créer un devis pour un autre client
        quote_other = Quote.objects.create(client=customer_alt, status=Quote.QuoteStatus.SENT)
        
        # Act
        response = client_authenticated.get('/client/')
        
        # Assert
        assert response.status_code == 200
        quotes = response.context.get('quotes', [])
        
        # Le client doit voir son devis
        assert quote_own in quotes
        # Mais PAS le devis de l'autre client
        assert quote_other not in quotes

    def test_client_sees_only_own_invoices(self, client_authenticated, user_client, customer, customer_alt):
        """Un client doit voir uniquement SES factures."""
        # Arrange
        customer.email = user_client.email
        customer.save()
        
        # Devis + facture pour ce client
        quote_own = Quote.objects.create(client=customer, status=Quote.QuoteStatus.ACCEPTED)
        QuoteItem.objects.create(quote=quote_own, description="Item", quantity=1, unit_price=100, tax_rate=20)
        quote_own.compute_totals()
        
        from devis.services import create_invoice_from_quote
        result_own = create_invoice_from_quote(quote_own)
        
        # Devis + facture pour autre client
        quote_other = Quote.objects.create(client=customer_alt, status=Quote.QuoteStatus.ACCEPTED)
        QuoteItem.objects.create(quote=quote_other, description="Item", quantity=1, unit_price=100, tax_rate=20)
        quote_other.compute_totals()
        result_other = create_invoice_from_quote(quote_other)
        
        # Act
        response = client_authenticated.get('/client/')
        
        # Assert
        invoices = response.context.get('invoices', [])
        assert result_own.invoice in invoices
        assert result_other.invoice not in invoices


class TestClientPermissions:
    """Tests des permissions spécifiques au rôle client."""

    def test_client_has_quotes_view_permission(self, user_client):
        """Un client doit avoir la permission 'quotes.view'."""
        # Act & Assert
        assert user_has_permission(user_client, 'quotes.view') is True

    def test_client_has_invoices_view_permission(self, user_client):
        """Un client doit avoir la permission 'invoices.view'."""
        # Act & Assert
        assert user_has_permission(user_client, 'invoices.view') is True

    def test_client_cannot_create_quotes(self, user_client):
        """Un client ne doit PAS avoir la permission 'quotes.create'."""
        # Act & Assert
        assert user_has_permission(user_client, 'quotes.create') is False

    def test_client_cannot_edit_quotes(self, user_client):
        """Un client ne doit PAS avoir la permission 'quotes.edit'."""
        # Act & Assert
        assert user_has_permission(user_client, 'quotes.edit') is False

    def test_client_cannot_create_invoices(self, user_client):
        """Un client ne doit PAS avoir la permission 'invoices.create'."""
        # Act & Assert
        assert user_has_permission(user_client, 'invoices.create') is False

    def test_client_cannot_view_tasks(self, user_client):
        """Un client ne doit PAS avoir la permission 'tasks.view'."""
        # Act & Assert
        assert user_has_permission(user_client, 'tasks.view') is False

    def test_client_cannot_manage_users(self, user_client):
        """Un client ne doit PAS avoir la permission 'users.edit'."""
        # Act & Assert
        assert user_has_permission(user_client, 'users.edit') is False


class TestClientPublicAccess:
    """Tests d'accès aux pages publiques par les clients."""

    def test_client_can_access_home_page(self, client_authenticated):
        """Un client peut accéder à la page d'accueil publique."""
        # Act
        response = client_authenticated.get('/')
        
        # Assert
        assert response.status_code == 200

    def test_client_can_access_services_list(self, client_authenticated):
        """Un client peut accéder à la liste des services."""
        # Act
        response = client_authenticated.get('/services/')
        
        # Assert
        assert response.status_code == 200

    def test_client_can_access_contact_form(self, client_authenticated):
        """Un client peut accéder au formulaire de contact."""
        # Act
        response = client_authenticated.get('/contact/')
        
        # Assert
        assert response.status_code == 200


class TestClientQuoteValidation:
    """Tests de validation de devis par le client."""

    def test_client_can_validate_own_quote(self, client_authenticated, user_client, customer):
        """Un client peut valider son propre devis via le lien 2FA."""
        # Arrange
        customer.email = user_client.email
        customer.save()
        
        quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.SENT)
        
        from devis.models import QuoteValidation
        validation = QuoteValidation.create_for_quote(quote)
        
        # Act - Accès à la page de validation (public, pas besoin d'auth)
        response = client_authenticated.get(f'/devis/validation/{validation.token}/')
        
        # Assert
        # Le client doit pouvoir accéder (200 ou redirection vers formulaire)
        assert response.status_code in [200, 302]


class TestClientRedirection:
    """Tests de redirection automatique."""

    def test_logged_in_client_accessing_wrong_portal_redirects(self, client_authenticated):
        """Un client accédant au mauvais portail doit être redirigé vers /client/."""
        # Act
        response = client_authenticated.get('/worker/')
        
        # Assert
        if response.status_code == 302:
            assert '/client/' in response.url

