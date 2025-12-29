"""
Configuration pytest et fixtures communes pour les tests NetExpress.

Ce fichier contient les fixtures réutilisables pour tous les tests
de l'ERP NetExpress.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.models import User, Group
from django.test import Client as DjangoClient

from accounts.models import Profile
from crm.models import Customer
from devis.models import Quote, QuoteItem, QuoteValidation
from factures.models import Invoice, InvoiceItem
from services.models import Service, Category
from tasks.models import Task


# ============================================================================
# FIXTURES UTILISATEURS
# ============================================================================

@pytest.fixture
def user_client(db):
    """Utilisateur avec rôle client."""
    user = User.objects.create_user(
        username="client_test",
        password="password123",
        email="client@test.com"
    )
    Profile.objects.create(user=user, role=Profile.ROLE_CLIENT)
    return user


@pytest.fixture
def user_worker(db):
    """Utilisateur avec rôle worker."""
    user = User.objects.create_user(
        username="worker_test",
        password="password123",
        email="worker@test.com"
    )
    Profile.objects.create(user=user, role=Profile.ROLE_WORKER)
    # Ajouter à une équipe
    group = Group.objects.create(name="Équipe A")
    user.groups.add(group)
    return user


@pytest.fixture
def user_admin_business(db):
    """Utilisateur avec rôle admin business."""
    user = User.objects.create_user(
        username="admin_business",
        password="password123",
        email="admin@test.com",
        is_staff=True
    )
    Profile.objects.create(user=user, role="admin_business")
    return user


@pytest.fixture
def user_superuser(db):
    """Superuser (admin technique)."""
    return User.objects.create_superuser(
        username="super_admin",
        password="password123",
        email="super@test.com"
    )


# ============================================================================
# FIXTURES CLIENTS CRM
# ============================================================================

@pytest.fixture
def customer(db):
    """Client standard pour les tests."""
    return Customer.objects.create(
        full_name="Client Test",
        email="client@test.com",
        phone="0123456789",
        address_line="123 Rue de Test",
        city="Paris",
        zip_code="75001"
    )


@pytest.fixture
def customer_alt(db):
    """Client alternatif pour tests d'isolation."""
    return Customer.objects.create(
        full_name="Autre Client",
        email="autre@test.com",
        phone="0987654321"
    )


# ============================================================================
# FIXTURES SERVICES
# ============================================================================

@pytest.fixture
def category_nettoyage(db):
    """Catégorie Nettoyage."""
    return Category.objects.create(
        name="Nettoyage",
        slug="nettoyage"
    )


@pytest.fixture
def category_espaces_verts(db):
    """Catégorie Espaces Verts."""
    return Category.objects.create(
        name="Espaces Verts",
        slug="espaces-verts"
    )


@pytest.fixture
def service_nettoyage(category_nettoyage):
    """Service de nettoyage standard."""
    return Service.objects.create(
        title="Nettoyage Bureaux",
        category=category_nettoyage,
        description="Nettoyage professionnel de bureaux",
        short_description="Nettoyage bureaux pro",
        unit_type="forfait",
        duration_minutes=120,
        is_active=True
    )


@pytest.fixture
def service_jardinage(category_espaces_verts):
    """Service de jardinage."""
    return Service.objects.create(
        title="Tonte de Pelouse",
        category=category_espaces_verts,
        description="Tonte professionnelle",
        unit_type="m²",
        duration_minutes=60,
        is_active=True
    )


# ============================================================================
# FIXTURES DEVIS
# ============================================================================

@pytest.fixture
def quote_draft(customer):
    """Devis en brouillon sans lignes."""
    return Quote.objects.create(
        client=customer,
        status=Quote.QuoteStatus.DRAFT
    )


@pytest.fixture
def quote_with_items(customer, service_nettoyage):
    """Devis en brouillon avec 2 lignes."""
    quote = Quote.objects.create(
        client=customer,
        status=Quote.QuoteStatus.DRAFT
    )
    QuoteItem.objects.create(
        quote=quote,
        service=service_nettoyage,
        description="Nettoyage complet",
        quantity=Decimal("1.00"),
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("20.00")
    )
    QuoteItem.objects.create(
        quote=quote,
        description="Produits spéciaux",
        quantity=Decimal("2.00"),
        unit_price=Decimal("50.00"),
        tax_rate=Decimal("20.00")
    )
    quote.compute_totals()
    return quote


@pytest.fixture
def quote_sent(quote_with_items):
    """Devis envoyé (statut SENT)."""
    quote_with_items.status = Quote.QuoteStatus.SENT
    quote_with_items.save()
    return quote_with_items


@pytest.fixture
def quote_accepted(quote_with_items):
    """Devis accepté (statut ACCEPTED)."""
    quote_with_items.status = Quote.QuoteStatus.ACCEPTED
    quote_with_items.save()
    return quote_with_items


@pytest.fixture
def quote_validation(quote_sent):
    """Validation 2FA pour un devis envoyé."""
    return QuoteValidation.create_for_quote(quote_sent, ttl_minutes=15)


# ============================================================================
# FIXTURES FACTURES
# ============================================================================

@pytest.fixture
def invoice_draft(db):
    """Facture en brouillon sans lignes."""
    return Invoice.objects.create(
        status=Invoice.InvoiceStatus.DRAFT
    )


@pytest.fixture
def invoice_with_items(invoice_draft):
    """Facture avec 2 lignes."""
    InvoiceItem.objects.create(
        invoice=invoice_draft,
        description="Service A",
        quantity=1,
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("20.00")
    )
    InvoiceItem.objects.create(
        invoice=invoice_draft,
        description="Service B",
        quantity=2,
        unit_price=Decimal("50.00"),
        tax_rate=Decimal("20.00")
    )
    invoice_draft.compute_totals()
    return invoice_draft


@pytest.fixture
def invoice_from_quote(quote_accepted):
    """Facture créée depuis un devis accepté."""
    from devis.services import create_invoice_from_quote
    result = create_invoice_from_quote(quote_accepted)
    return result.invoice


# ============================================================================
# FIXTURES TÂCHES
# ============================================================================

@pytest.fixture
def task_upcoming(db):
    """Tâche à venir."""
    today = date.today()
    return Task.objects.create(
        title="Tâche Future",
        description="Description de la tâche",
        location="Paris",
        team="Équipe A",
        start_date=today + timedelta(days=5),
        due_date=today + timedelta(days=10)
    )


@pytest.fixture
def task_in_progress(db):
    """Tâche en cours."""
    today = date.today()
    return Task.objects.create(
        title="Tâche en Cours",
        location="Lyon",
        team="Équipe B",
        start_date=today,
        due_date=today + timedelta(days=5)
    )


@pytest.fixture
def task_overdue(db):
    """Tâche en retard."""
    today = date.today()
    return Task.objects.create(
        title="Tâche en Retard",
        location="Marseille",
        team="Équipe A",
        start_date=today - timedelta(days=10),
        due_date=today - timedelta(days=2)
    )


@pytest.fixture
def task_almost_overdue(db):
    """Tâche presque en retard (due demain)."""
    today = date.today()
    return Task.objects.create(
        title="Tâche Urgente",
        location="Nice",
        team="Équipe B",
        start_date=today - timedelta(days=2),
        due_date=today + timedelta(days=1)
    )


# ============================================================================
# FIXTURES CLIENTS DJANGO (pour tests de vues)
# ============================================================================

@pytest.fixture
def client_authenticated(user_client):
    """Client Django authentifié avec rôle client."""
    client = DjangoClient()
    client.force_login(user_client)
    return client


@pytest.fixture
def client_worker(user_worker):
    """Client Django authentifié avec rôle worker."""
    client = DjangoClient()
    client.force_login(user_worker)
    return client


@pytest.fixture
def client_admin(user_admin_business):
    """Client Django authentifié avec rôle admin business."""
    client = DjangoClient()
    client.force_login(user_admin_business)
    return client


@pytest.fixture
def client_superuser(user_superuser):
    """Client Django authentifié avec rôle superuser."""
    client = DjangoClient()
    client.force_login(user_superuser)
    return client


# ============================================================================
# FIXTURES UTILITAIRES
# ============================================================================

@pytest.fixture
def mock_email_backend(settings):
    """Configure le backend email en mode console pour les tests."""
    settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    return settings

