"""
Property-based tests for Client Portal data isolation.

**Feature: netexpress-v2-transformation, Property 2: Data isolation by user role**
**Validates: Requirements 2.1, 2.4, 3.1**
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import from_model, TestCase
from django.contrib.auth.models import User, Group
from django.test import RequestFactory

from devis.models import Client, Quote
from factures.models import Invoice
from accounts.models import Profile
from core.services.document_service import ClientDocumentService


# Strategies for generating test data
@st.composite
def user_with_role(draw, role='client'):
    """Generate a user with a specific role."""
    username = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    email = f"{username}@example.com"
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password='testpass123'
    )
    
    # Create profile with role
    Profile.objects.filter(user=user).update(role=role)
    
    # Add to appropriate group
    if role == 'client':
        group, _ = Group.objects.get_or_create(name='Clients')
        user.groups.add(group)
    elif role == 'worker':
        group, _ = Group.objects.get_or_create(name='Workers')
        user.groups.add(group)
    
    return user


@st.composite
def client_with_email(draw):
    """Generate a Client instance with a valid email."""
    # Generate unique identifier to ensure unique emails using Hypothesis strategies
    unique_id = draw(st.text(min_size=8, max_size=8, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))))
    
    full_name = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    # Ensure unique email by adding unique_id
    email_prefix = draw(st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))))
    email = f"{email_prefix}_{unique_id}@example.com"
    phone = draw(st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=('Nd',))))
    
    client = Client.objects.create(
        full_name=full_name,
        email=email,
        phone=phone
    )
    return client


@st.composite
def quote_for_client(draw, client):
    """Generate a Quote for a specific client."""
    from decimal import Decimal
    from datetime import date
    
    quote = Quote.objects.create(
        client=client,
        status=draw(st.sampled_from(['draft', 'sent', 'accepted', 'rejected'])),
        issue_date=date.today(),
        total_ht=Decimal('100.00'),
        tva=Decimal('20.00'),
        total_ttc=Decimal('120.00')
    )
    return quote


@st.composite
def invoice_for_quote(draw, quote):
    """Generate an Invoice for a specific quote."""
    from decimal import Decimal
    from datetime import date
    
    invoice = Invoice.objects.create(
        quote=quote,
        status=draw(st.sampled_from(['draft', 'sent', 'paid', 'overdue'])),
        issue_date=date.today(),
        total_ht=Decimal('100.00'),
        tva=Decimal('20.00'),
        total_ttc=Decimal('120.00')
    )
    return invoice


class TestDataIsolationProperties(TestCase):
    """Property-based tests for data isolation by user role."""
    
    def setUp(self):
        """Set up test environment."""
        # Ensure groups exist
        Group.objects.get_or_create(name='Clients')
        Group.objects.get_or_create(name='Workers')
    
    @settings(max_examples=10, deadline=None)
    @given(
        client1_data=client_with_email(),
        client2_data=client_with_email(),
        data=st.data(),
    )
    def test_property_client_can_only_access_own_quotes(self, client1_data, client2_data, data):
        """
        Property 2: Data isolation by user role
        
        For any authenticated client user, all displayed quotes should be filtered
        to show only quotes belonging to that specific client's email.
        
        **Validates: Requirements 2.1, 2.4**
        """
        # Create two clients with different emails
        client1 = client1_data
        client2 = client2_data
        
        # Ensure emails are different
        if client1.email == client2.email:
            client2.email = f"different_{client2.email}"
            client2.save()
        
        # Create user accounts for both clients
        user1 = User.objects.create_user(
            username=f"client1_{client1.pk}",
            email=client1.email,
            password='testpass123'
        )
        Profile.objects.filter(user=user1).update(role='client')
        
        user2 = User.objects.create_user(
            username=f"client2_{client2.pk}",
            email=client2.email,
            password='testpass123'
        )
        Profile.objects.filter(user=user2).update(role='client')
        
        # Create quotes for both clients using data.draw()
        quote1 = data.draw(quote_for_client(client1))
        quote2 = data.draw(quote_for_client(client2))
        
        # Test: User1 should only see their own quotes
        user1_quotes = ClientDocumentService.get_accessible_quotes(user1)
        assert quote1 in user1_quotes, "User should see their own quote"
        assert quote2 not in user1_quotes, "User should not see other client's quote"
        
        # Test: User2 should only see their own quotes
        user2_quotes = ClientDocumentService.get_accessible_quotes(user2)
        assert quote2 in user2_quotes, "User should see their own quote"
        assert quote1 not in user2_quotes, "User should not see other client's quote"
        
        # Test: Access control for specific quotes
        assert ClientDocumentService.can_access_quote(user1, quote1), "User should have access to their own quote"
        assert not ClientDocumentService.can_access_quote(user1, quote2), "User should not have access to other's quote"
        assert ClientDocumentService.can_access_quote(user2, quote2), "User should have access to their own quote"
        assert not ClientDocumentService.can_access_quote(user2, quote1), "User should not have access to other's quote"
    
    @settings(max_examples=10, deadline=None)
    @given(
        client1_data=client_with_email(),
        client2_data=client_with_email(),
        data=st.data(),
    )
    def test_property_client_can_only_access_own_invoices(self, client1_data, client2_data, data):
        """
        Property 2: Data isolation by user role (invoices)
        
        For any authenticated client user, all displayed invoices should be filtered
        to show only invoices linked to quotes belonging to that specific client.
        
        **Validates: Requirements 2.1, 2.4**
        """
        # Create two clients with different emails
        client1 = client1_data
        client2 = client2_data
        
        # Ensure emails are different
        if client1.email == client2.email:
            client2.email = f"different_{client2.email}"
            client2.save()
        
        # Create user accounts for both clients
        user1 = User.objects.create_user(
            username=f"client1_{client1.pk}",
            email=client1.email,
            password='testpass123'
        )
        Profile.objects.filter(user=user1).update(role='client')
        
        user2 = User.objects.create_user(
            username=f"client2_{client2.pk}",
            email=client2.email,
            password='testpass123'
        )
        Profile.objects.filter(user=user2).update(role='client')
        
        # Create quotes and invoices for both clients using data.draw()
        quote1 = data.draw(quote_for_client(client1))
        invoice1 = data.draw(invoice_for_quote(quote1))
        
        quote2 = data.draw(quote_for_client(client2))
        invoice2 = data.draw(invoice_for_quote(quote2))
        
        # Test: User1 should only see their own invoices
        user1_invoices = ClientDocumentService.get_accessible_invoices(user1)
        assert invoice1 in user1_invoices, "User should see their own invoice"
        assert invoice2 not in user1_invoices, "User should not see other client's invoice"
        
        # Test: User2 should only see their own invoices
        user2_invoices = ClientDocumentService.get_accessible_invoices(user2)
        assert invoice2 in user2_invoices, "User should see their own invoice"
        assert invoice1 not in user2_invoices, "User should not see other client's invoice"
        
        # Test: Access control for specific invoices
        assert ClientDocumentService.can_access_invoice(user1, invoice1), "User should have access to their own invoice"
        assert not ClientDocumentService.can_access_invoice(user1, invoice2), "User should not have access to other's invoice"
        assert ClientDocumentService.can_access_invoice(user2, invoice2), "User should have access to their own invoice"
        assert not ClientDocumentService.can_access_invoice(user2, invoice1), "User should not have access to other's invoice"
    
    @settings(max_examples=10, deadline=None)
    @given(
        client_data=client_with_email(),
        data=st.data(),
    )
    def test_property_staff_can_access_all_documents(self, client_data, data):
        """
        Property 2: Data isolation by user role (staff access)
        
        For any staff/admin user, all documents should be accessible regardless
        of which client they belong to.
        
        **Validates: Requirements 2.1, 2.4**
        """
        # Create a client and their documents using data.draw()
        client = client_data
        quote = data.draw(quote_for_client(client))
        invoice = data.draw(invoice_for_quote(quote))
        
        # Create a staff user
        staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Test: Staff should see all quotes
        staff_quotes = ClientDocumentService.get_accessible_quotes(staff_user)
        assert quote in staff_quotes, "Staff should see all quotes"
        
        # Test: Staff should see all invoices
        staff_invoices = ClientDocumentService.get_accessible_invoices(staff_user)
        assert invoice in staff_invoices, "Staff should see all invoices"
        
        # Test: Staff should have access to any document
        assert ClientDocumentService.can_access_quote(staff_user, quote), "Staff should have access to any quote"
        assert ClientDocumentService.can_access_invoice(staff_user, invoice), "Staff should have access to any invoice"
    
    @settings(max_examples=10, deadline=None)
    @given(
        client_data=client_with_email(),
        data=st.data(),
    )
    def test_property_unauthenticated_users_see_no_documents(self, client_data, data):
        """
        Property 2: Data isolation by user role (unauthenticated)
        
        For any unauthenticated user, no documents should be accessible.
        
        **Validates: Requirements 2.1, 2.4**
        """
        # Create a client and their documents using data.draw()
        client = client_data
        quote = data.draw(quote_for_client(client))
        invoice = data.draw(invoice_for_quote(quote))
        
        # Create an unauthenticated user (anonymous)
        from django.contrib.auth.models import AnonymousUser
        anon_user = AnonymousUser()
        
        # Test: Anonymous users should see no quotes
        anon_quotes = ClientDocumentService.get_accessible_quotes(anon_user)
        assert quote not in anon_quotes, "Anonymous users should not see any quotes"
        assert anon_quotes.count() == 0, "Anonymous users should have empty quote list"
        
        # Test: Anonymous users should see no invoices
        anon_invoices = ClientDocumentService.get_accessible_invoices(anon_user)
        assert invoice not in anon_invoices, "Anonymous users should not see any invoices"
        assert anon_invoices.count() == 0, "Anonymous users should have empty invoice list"
        
        # Test: Anonymous users should not have access to any document
        assert not ClientDocumentService.can_access_quote(anon_user, quote), "Anonymous users should not access quotes"
        assert not ClientDocumentService.can_access_invoice(anon_user, invoice), "Anonymous users should not access invoices"