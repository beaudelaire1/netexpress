"""
Tests fonctionnels et métier complets pour NetExpress ERP.
Valide les phases 0 à 7 du projet et l'architecture orientée services.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import Profile
from devis.models import Quote, QuoteItem, QuoteValidation, Client as DevisClient
from devis.services import QuoteStatusError, create_invoice_from_quote
from factures.models import Invoice, InvoiceItem
from tasks.models import Task
from services.models import Service, Category

User = get_user_model()

pytestmark = pytest.mark.django_db

class TestERPPermissions:
    """Vérification des permissions par rôle et isolation des données."""

    @pytest.fixture
    def setup_users(self):
        # Client
        client_user = User.objects.create_user(username='client_test', password='pass123', email='client@test.com')
        # Profile is auto-created by signal, just update it
        client_user.profile.role = Profile.ROLE_CLIENT
        client_user.profile.save()
        
        # Worker
        worker_user = User.objects.create_user(username='worker_test', password='pass123', email='worker@test.com')
        worker_user.profile.role = Profile.ROLE_WORKER
        worker_user.profile.save()
        
        # Admin Business
        admin_user = User.objects.create_user(username='admin_test', password='pass123')
        admin_user.profile.role = Profile.ROLE_ADMIN_BUSINESS
        admin_user.profile.save()
        
        return {
            'client': client_user,
            'worker': worker_user,
            'admin': admin_user
        }

    def test_dashboard_access_restrictions(self, setup_users):
        c = Client()
        
        # 1. Test Client access
        c.login(username='client_test', password='pass123')
        assert c.get(reverse('client_portal:dashboard')).status_code == 200
        # Should redirect to their own portal (302) instead of 403
        response = c.get(reverse('worker:worker_dashboard'))
        assert response.status_code == 302
        assert response.url == reverse('client_portal:dashboard')
        c.logout()

        # 2. Test Worker access
        c.login(username='worker_test', password='pass123')
        assert c.get(reverse('worker:worker_dashboard')).status_code == 200
        response = c.get(reverse('client_portal:dashboard'))
        assert response.status_code == 302
        assert response.url == reverse('worker:worker_dashboard')
        c.logout()

        # 3. Test Admin Business access
        c.login(username='admin_test', password='pass123')
        assert c.get(reverse('core:admin_dashboard')).status_code == 200
        # Admin business is also restricted to its dashboard
        response = c.get(reverse('client_portal:dashboard'))
        assert response.status_code == 302
        assert response.url == reverse('core:admin_dashboard')

    def test_client_data_isolation(self, setup_users):
        """Un client ne doit voir que ses propres devis."""
        c = Client()
        
        # Création de deux clients (devis.Client)
        dc1 = DevisClient.objects.create(full_name="Client 1", email="client@test.com")
        dc2 = DevisClient.objects.create(full_name="Client 2", email="other@test.com")
        
        # Création de devis
        q1 = Quote.objects.create(client=dc1, number="DEV-2025-001")
        q2 = Quote.objects.create(client=dc2, number="DEV-2025-002")
        
        c.login(username='client_test', password='pass123')
        response = c.get(reverse('client_portal:dashboard'))
        
        assert "DEV-2025-001" in response.content.decode()
        assert "DEV-2025-002" not in response.content.decode()


class TestERPBusinessLogic:
    """Validation de la logique métier (Calculs, Transitions, Conversions)."""

    def test_quote_totals_and_conversion(self):
        # Setup
        dc = DevisClient.objects.create(full_name="Test Business", email="biz@test.com")
        quote = Quote.objects.create(client=dc, number="DEV-BIZ-001")
        
        # Ajout d'items
        QuoteItem.objects.create(
            quote=quote, description="Item 1", quantity=2, unit_price=100, tax_rate=20
        )
        QuoteItem.objects.create(
            quote=quote, description="Item 2", quantity=1, unit_price=50, tax_rate=10
        )
        
        # 1. Test calcul totaux
        quote.compute_totals()
        # Item 1: 200 HT + 40 TVA = 240 TTC
        # Item 2: 50 HT + 5 TVA = 55 TTC
        # Total: 250 HT, 45 TVA, 295 TTC
        assert quote.total_ht == Decimal("250.00")
        assert quote.tva == Decimal("45.00")
        assert quote.total_ttc == Decimal("295.00")
        
        # 2. Test blocage conversion si non ACCEPTED
        with pytest.raises(QuoteStatusError):
            create_invoice_from_quote(quote)
            
        # 3. Test conversion réussie
        quote.status = Quote.QuoteStatus.ACCEPTED
        quote.save()
        
        result = create_invoice_from_quote(quote)
        invoice = result.invoice
        
        assert invoice.total_ttc == quote.total_ttc
        assert invoice.quote == quote
        assert Quote.objects.get(pk=quote.pk).status == Quote.QuoteStatus.INVOICED
        assert invoice.invoice_items.count() == 2

    def test_quote_validation_2fa(self):
        dc = DevisClient.objects.create(full_name="Test 2FA", email="2fa@test.com")
        quote = Quote.objects.create(client=dc, status=Quote.QuoteStatus.SENT)
        
        validation = QuoteValidation.create_for_quote(quote)
        assert len(validation.code) == 6
        
        # Code erroné
        assert validation.verify("000000") is False
        assert validation.is_confirmed is False
        
        # Code correct
        assert validation.verify(validation.code) is True
        assert validation.is_confirmed is True


class TestERPWorkflow:
    """Flux critiques de bout en bout."""

    def test_full_cycle_quote_to_task(self):
        # 1. Demande de devis -> Devis
        dc = DevisClient.objects.create(full_name="End To End", email="e2e@test.com")
        quote = Quote.objects.create(client=dc, status=Quote.QuoteStatus.ACCEPTED)
        QuoteItem.objects.create(quote=quote, description="Travaux", quantity=1, unit_price=1000)
        quote.compute_totals()
        
        # 2. Conversion en facture
        invoice = create_invoice_from_quote(quote).invoice
        assert invoice.total_ttc == Decimal("1200.00") # 1000 + 20% TVA par défaut
        
        # 3. Création de tâche liée (Manuel ou auto selon implémentation)
        task = Task.objects.create(
            title=f"Intervention pour {dc.full_name}",
            start_date=date.today(),
            due_date=date.today() + timedelta(days=2),
            status=Task.STATUS_IN_PROGRESS
        )
        assert task.is_due_soon() is True
