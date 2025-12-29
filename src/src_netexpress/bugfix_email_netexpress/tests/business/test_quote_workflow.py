"""
Tests du flux métier complet pour les devis.

Couvre:
- Création de devis avec calcul automatique
- Numérotation unique
- Validation 2FA
- Transitions de statuts
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from devis.models import Quote, QuoteItem, QuoteValidation
from crm.models import Customer


pytestmark = pytest.mark.django_db


class TestQuoteCreationAndCalculations:
    """Tests de création et calculs de devis."""

    def test_quote_creation_with_items_calculates_totals(self, customer):
        """TEST-DEVIS-001: Un devis avec lignes doit calculer automatiquement ses totaux."""
        # Arrange
        quote = Quote.objects.create(
            client=customer,
            status=Quote.QuoteStatus.DRAFT
        )
        QuoteItem.objects.create(
            quote=quote,
            description="Service A",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("20.00")
        )
        QuoteItem.objects.create(
            quote=quote,
            description="Service B",
            quantity=Decimal("1.00"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("20.00")
        )
        
        # Act
        quote.compute_totals()
        
        # Assert
        assert quote.total_ht == Decimal("250.00")  # (2*100 + 1*50)
        assert quote.tva == Decimal("50.00")        # 250 * 0.20
        assert quote.total_ttc == Decimal("300.00") # 250 + 50

    def test_quote_empty_has_zero_totals(self, customer):
        """Un devis sans lignes doit avoir des totaux à zéro."""
        # Arrange
        quote = Quote.objects.create(
            client=customer,
            status=Quote.QuoteStatus.DRAFT
        )
        
        # Act
        quote.compute_totals()
        
        # Assert
        assert quote.total_ht == Decimal("0.00")
        assert quote.tva == Decimal("0.00")
        assert quote.total_ttc == Decimal("0.00")

    def test_quote_calculates_with_multiple_tax_rates(self, customer):
        """Les calculs doivent gérer plusieurs taux de TVA."""
        # Arrange
        quote = Quote.objects.create(client=customer)
        QuoteItem.objects.create(
            quote=quote,
            description="Item 20%",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("20.00")
        )
        QuoteItem.objects.create(
            quote=quote,
            description="Item 10%",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("10.00")
        )
        QuoteItem.objects.create(
            quote=quote,
            description="Item 5.5%",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("5.50")
        )
        
        # Act
        quote.compute_totals()
        
        # Assert
        assert quote.total_ht == Decimal("300.00")  # 100 + 100 + 100
        assert quote.tva == Decimal("35.50")         # 20 + 10 + 5.5
        assert quote.total_ttc == Decimal("335.50")  # 300 + 35.5

    def test_quote_decimal_precision(self, customer):
        """Les calculs doivent respecter la précision décimale (ROUND_HALF_UP)."""
        # Arrange
        quote = Quote.objects.create(client=customer)
        QuoteItem.objects.create(
            quote=quote,
            description="Item décimal",
            quantity=Decimal("1.33"),
            unit_price=Decimal("7.99"),
            tax_rate=Decimal("20.00")
        )
        
        # Act
        quote.compute_totals()
        
        # Assert
        # 1.33 * 7.99 = 10.6267 → arrondi à 10.63 (HT)
        # 10.63 * 0.20 = 2.126 → arrondi à 2.13 (TVA)
        # TTC = 10.63 + 2.13 = 12.76
        assert quote.total_ht == Decimal("10.63")
        assert quote.tva == Decimal("2.13")
        assert quote.total_ttc == Decimal("12.76")


class TestQuoteNumbering:
    """Tests de numérotation automatique des devis."""

    def test_quote_numbering_uniqueness(self, customer):
        """TEST-DEVIS-002: Les devis doivent avoir des numéros séquentiels uniques par année."""
        # Arrange
        year = date.today().year
        
        # Act
        q1 = Quote.objects.create(client=customer)
        q2 = Quote.objects.create(client=customer)
        
        # Assert
        assert q1.number == f"DEV-{year}-001"
        assert q2.number == f"DEV-{year}-002"
        assert Quote.objects.filter(number__startswith=f"DEV-{year}-").count() == 2

    def test_quote_number_generation_on_save(self, customer):
        """Le numéro doit être généré automatiquement au save si vide."""
        # Arrange
        quote = Quote(client=customer)
        
        # Assert - avant save
        assert quote.number == ""
        
        # Act
        quote.save()
        
        # Assert - après save
        assert quote.number.startswith("DEV-")
        assert len(quote.number.split("-")) == 3

    def test_quote_number_preserved_on_update(self, customer):
        """Le numéro ne doit pas changer lors d'une mise à jour."""
        # Arrange
        quote = Quote.objects.create(client=customer)
        original_number = quote.number
        
        # Act
        quote.message = "Message mis à jour"
        quote.save()
        
        # Assert
        assert quote.number == original_number


class TestQuoteValidation2FA:
    """Tests de validation 2FA des devis."""

    def test_quote_validation_requires_correct_code(self, quote_sent):
        """TEST-DEVIS-003: La validation d'un devis doit nécessiter un code 2FA correct."""
        # Arrange
        validation = QuoteValidation.create_for_quote(quote_sent, ttl_minutes=15)
        
        # Act - Code incorrect
        result_wrong = validation.verify("000000")
        
        # Assert
        assert result_wrong is False
        assert validation.attempts == 1
        assert validation.confirmed_at is None
        
        # Act - Code correct
        result_ok = validation.verify(validation.code)
        
        # Assert
        assert result_ok is True
        assert validation.is_confirmed is True
        assert validation.confirmed_at is not None

    def test_quote_validation_expiration(self, quote_sent):
        """TEST-DEVIS-004: Un code expiré ne doit pas permettre la validation."""
        # Arrange
        validation = QuoteValidation.create_for_quote(quote_sent, ttl_minutes=0)
        
        # Simuler expiration
        validation.expires_at = timezone.now() - timedelta(minutes=1)
        validation.save()
        
        # Act
        result = validation.verify(validation.code)
        
        # Assert
        assert result is False
        assert validation.is_expired is True

    def test_quote_validation_max_attempts(self, quote_sent):
        """La validation doit bloquer après le nombre max de tentatives."""
        # Arrange
        validation = QuoteValidation.create_for_quote(quote_sent, ttl_minutes=15)
        max_attempts = 5
        
        # Act - Tenter 5 fois avec mauvais code
        for _ in range(max_attempts):
            validation.verify("wrong_code", max_attempts=max_attempts)
        
        # Assert
        assert validation.attempts == max_attempts
        
        # Même avec le bon code, ça doit échouer
        result = validation.verify(validation.code, max_attempts=max_attempts)
        assert result is False

    def test_quote_validation_creates_unique_token(self, quote_sent):
        """Chaque validation doit avoir un token unique."""
        # Arrange & Act
        validation1 = QuoteValidation.create_for_quote(quote_sent)
        validation2 = QuoteValidation.create_for_quote(quote_sent)
        
        # Assert
        assert validation1.token != validation2.token
        assert validation1.code != validation2.code

    def test_quote_validation_invalidates_previous(self, quote_sent):
        """Créer une nouvelle validation doit invalider les précédentes."""
        # Arrange
        validation1 = QuoteValidation.create_for_quote(quote_sent)
        token1 = validation1.token
        
        # Act
        validation2 = QuoteValidation.create_for_quote(quote_sent)
        
        # Assert
        # validation1 doit être supprimée
        assert not QuoteValidation.objects.filter(token=token1).exists()
        # Seule validation2 existe
        assert QuoteValidation.objects.filter(quote=quote_sent, confirmed_at__isnull=True).count() == 1


class TestQuoteStatusTransitions:
    """Tests des transitions de statut des devis."""

    def test_quote_can_transition_draft_to_sent(self, quote_draft):
        """Transition DRAFT → SENT autorisée."""
        # Act
        quote_draft.status = Quote.QuoteStatus.SENT
        quote_draft.save()
        
        # Assert
        assert quote_draft.status == Quote.QuoteStatus.SENT

    def test_quote_can_transition_sent_to_accepted(self, quote_sent):
        """Transition SENT → ACCEPTED autorisée."""
        # Act
        quote_sent.status = Quote.QuoteStatus.ACCEPTED
        quote_sent.save()
        
        # Assert
        assert quote_sent.status == Quote.QuoteStatus.ACCEPTED

    def test_quote_can_transition_sent_to_rejected(self, quote_sent):
        """Transition SENT → REJECTED autorisée."""
        # Act
        quote_sent.status = Quote.QuoteStatus.REJECTED
        quote_sent.save()
        
        # Assert
        assert quote_sent.status == Quote.QuoteStatus.REJECTED


class TestQuotePublicToken:
    """Tests du token public pour consultation PDF."""

    def test_quote_generates_public_token_on_creation(self, customer):
        """Un devis doit avoir un public_token généré automatiquement."""
        # Act
        quote = Quote.objects.create(client=customer)
        
        # Assert
        assert quote.public_token is not None
        assert len(quote.public_token) > 0

    def test_quote_public_token_is_unique(self, customer):
        """Chaque devis doit avoir un token public unique."""
        # Act
        q1 = Quote.objects.create(client=customer)
        q2 = Quote.objects.create(client=customer)
        
        # Assert
        assert q1.public_token != q2.public_token

    def test_quote_public_token_persists(self, quote_draft):
        """Le token public ne doit pas changer lors des mises à jour."""
        # Arrange
        original_token = quote_draft.public_token
        
        # Act
        quote_draft.message = "Updated"
        quote_draft.save()
        
        # Assert
        assert quote_draft.public_token == original_token


class TestQuoteValidity:
    """Tests de la période de validité des devis."""

    def test_quote_sets_valid_until_30_days(self, customer):
        """Un devis doit avoir une validité par défaut de 30 jours."""
        # Arrange
        issue_date = date(2025, 1, 1)
        
        # Act
        quote = Quote.objects.create(
            client=customer,
            issue_date=issue_date
        )
        
        # Assert
        assert quote.valid_until == date(2025, 1, 31)  # +30 jours

    def test_quote_respects_custom_valid_until(self, customer):
        """Un devis avec valid_until personnalisé doit le conserver."""
        # Arrange
        custom_date = date(2025, 6, 30)
        
        # Act
        quote = Quote.objects.create(
            client=customer,
            valid_until=custom_date
        )
        
        # Assert
        assert quote.valid_until == custom_date


class TestQuoteAmountLetter:
    """Tests de conversion montant en lettres."""

    def test_quote_amount_letter_conversion(self, quote_with_items):
        """Le montant doit être converti en lettres."""
        # Act
        amount_text = quote_with_items.amount_letter()
        
        # Assert
        assert isinstance(amount_text, str)
        assert "euros" in amount_text.lower()
        assert len(amount_text) > 0

