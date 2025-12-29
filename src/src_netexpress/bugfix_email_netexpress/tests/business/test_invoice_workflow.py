"""
Tests du flux métier complet pour les factures.

Couvre:
- Conversion devis → facture
- Interdictions de conversion
- Numérotation unique
- Calculs avec remise
- Règles métier de facturation
"""

import pytest
from decimal import Decimal
from datetime import date
from django.db import transaction

from factures.models import Invoice, InvoiceItem
from devis.models import Quote, QuoteItem
from devis.services import (
    create_invoice_from_quote,
    QuoteStatusError,
    QuoteAlreadyInvoicedError
)


pytestmark = pytest.mark.django_db


class TestInvoiceConversionFromQuote:
    """Tests de conversion devis → facture."""

    def test_convert_accepted_quote_to_invoice(self, quote_accepted):
        """TEST-FACTURE-001: Un devis ACCEPTED doit pouvoir être converti en facture."""
        # Act
        result = create_invoice_from_quote(quote_accepted)
        
        # Assert
        assert result.invoice is not None
        assert result.invoice.quote == quote_accepted
        assert result.invoice.invoice_items.count() == quote_accepted.quote_items.count()
        assert result.invoice.total_ttc == quote_accepted.total_ttc
        assert quote_accepted.status == Quote.QuoteStatus.INVOICED

    def test_convert_quote_copies_all_items(self, quote_accepted, customer):
        """Le service doit copier TOUS les items du devis vers la facture."""
        # Arrange - Ajouter un 3ème item
        QuoteItem.objects.create(
            quote=quote_accepted,
            description="Item supplémentaire",
            quantity=Decimal("1.00"),
            unit_price=Decimal("75.00"),
            tax_rate=Decimal("10.00")
        )
        quote_accepted.compute_totals()
        
        # Act
        result = create_invoice_from_quote(quote_accepted)
        
        # Assert
        assert result.invoice.invoice_items.count() == 3
        items = list(result.invoice.invoice_items.all())
        descriptions = [item.description for item in items]
        assert "Item supplémentaire" in descriptions

    def test_convert_quote_preserves_totals(self, quote_accepted):
        """Les totaux de la facture doivent correspondre au devis."""
        # Arrange
        expected_ht = quote_accepted.total_ht
        expected_tva = quote_accepted.tva
        expected_ttc = quote_accepted.total_ttc
        
        # Act
        result = create_invoice_from_quote(quote_accepted)
        
        # Assert
        assert result.invoice.total_ht == expected_ht
        assert result.invoice.tva == expected_tva
        assert result.invoice.total_ttc == expected_ttc

    def test_prevent_invoice_from_draft_quote(self, quote_draft):
        """TEST-FACTURE-002: Un devis DRAFT ne doit PAS pouvoir être facturé."""
        # Act & Assert
        with pytest.raises(QuoteStatusError, match="n'est pas accepté"):
            create_invoice_from_quote(quote_draft)

    def test_prevent_invoice_from_sent_quote(self, quote_sent):
        """Un devis SENT (non validé) ne doit PAS pouvoir être facturé."""
        # Act & Assert
        with pytest.raises(QuoteStatusError, match="n'est pas accepté"):
            create_invoice_from_quote(quote_sent)

    def test_prevent_invoice_from_rejected_quote(self, customer):
        """Un devis REJECTED ne doit PAS pouvoir être facturé."""
        # Arrange
        quote = Quote.objects.create(
            client=customer,
            status=Quote.QuoteStatus.REJECTED
        )
        
        # Act & Assert
        with pytest.raises(QuoteStatusError, match="n'est pas accepté"):
            create_invoice_from_quote(quote)

    def test_prevent_duplicate_invoice_from_quote(self, quote_accepted):
        """TEST-FACTURE-003: Un devis déjà facturé ne doit pas être facturé deux fois."""
        # Arrange - Première facturation
        create_invoice_from_quote(quote_accepted)
        
        # Act & Assert
        with pytest.raises(QuoteAlreadyInvoicedError, match="existe déjà"):
            create_invoice_from_quote(quote_accepted)


class TestInvoiceNumbering:
    """Tests de numérotation automatique des factures."""

    def test_invoice_numbering_sequential(self):
        """TEST-FACTURE-004: Les factures doivent avoir des numéros séquentiels uniques."""
        # Arrange
        year = date.today().year
        
        # Act
        inv1 = Invoice.objects.create()
        inv2 = Invoice.objects.create()
        
        # Assert
        assert inv1.number == f"FAC-{year}-001"
        assert inv2.number == f"FAC-{year}-002"

    def test_invoice_number_generation_on_save(self):
        """Le numéro doit être généré automatiquement au save si vide."""
        # Arrange
        invoice = Invoice()
        
        # Assert - avant save
        assert invoice.number == ""
        
        # Act
        invoice.save()
        
        # Assert - après save
        assert invoice.number.startswith("FAC-")
        assert len(invoice.number.split("-")) == 3

    def test_invoice_number_preserved_on_update(self):
        """Le numéro ne doit pas changer lors d'une mise à jour."""
        # Arrange
        invoice = Invoice.objects.create()
        original_number = invoice.number
        
        # Act
        invoice.notes = "Notes mises à jour"
        invoice.save()
        
        # Assert
        assert invoice.number == original_number

    def test_invoice_number_uses_issue_date_year(self):
        """Le numéro doit utiliser l'année de issue_date."""
        # Arrange
        old_date = date(2023, 5, 15)
        
        # Act
        invoice = Invoice.objects.create(issue_date=old_date)
        
        # Assert
        assert invoice.number.startswith("FAC-2023-")


class TestInvoiceCalculations:
    """Tests des calculs de totaux sur factures."""

    def test_invoice_compute_totals_basic(self, invoice_draft):
        """compute_totals doit calculer HT, TVA et TTC correctement."""
        # Arrange
        InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item",
            quantity=1,
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("20.00")
        )
        
        # Act
        invoice_draft.compute_totals()
        
        # Assert
        assert invoice_draft.total_ht == Decimal("100.00")
        assert invoice_draft.tva == Decimal("20.00")
        assert invoice_draft.total_ttc == Decimal("120.00")
        assert invoice_draft.amount == Decimal("120.00")  # Compat field

    def test_invoice_discount_calculation(self, invoice_draft):
        """TEST-FACTURE-005: La remise doit être appliquée proportionnellement sur HT et TVA."""
        # Arrange
        invoice_draft.discount = Decimal("50.00")
        InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item",
            quantity=1,
            unit_price=Decimal("200.00"),
            tax_rate=Decimal("20.00")
        )
        
        # Act
        invoice_draft.compute_totals()
        
        # Assert
        # HT: 200 - 50 = 150
        # TVA: 150 * 0.20 = 30
        # TTC: 150 + 30 = 180
        assert invoice_draft.total_ht == Decimal("150.00")
        assert invoice_draft.tva == Decimal("30.00")
        assert invoice_draft.total_ttc == Decimal("180.00")

    def test_invoice_discount_exceeds_total(self, invoice_draft):
        """Une remise supérieure au total doit donner des montants à zéro."""
        # Arrange
        invoice_draft.discount = Decimal("500.00")  # Supérieur au total
        InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item",
            quantity=1,
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("20.00")
        )
        
        # Act
        invoice_draft.compute_totals()
        
        # Assert
        assert invoice_draft.total_ht == Decimal("0.00")
        assert invoice_draft.tva == Decimal("0.00")
        assert invoice_draft.total_ttc == Decimal("0.00")

    def test_invoice_multiple_items_calculation(self, invoice_draft):
        """Calcul avec plusieurs items de prix et TVA différents."""
        # Arrange
        InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item 1",
            quantity=2,
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("20.00")
        )
        InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item 2",
            quantity=3,
            unit_price=Decimal("30.00"),
            tax_rate=Decimal("10.00")
        )
        
        # Act
        invoice_draft.compute_totals()
        
        # Assert
        # Item 1: 2 * 50 = 100 HT, 100 * 0.20 = 20 TVA
        # Item 2: 3 * 30 = 90 HT, 90 * 0.10 = 9 TVA
        # Total: 190 HT, 29 TVA, 219 TTC
        assert invoice_draft.total_ht == Decimal("190.00")
        assert invoice_draft.tva == Decimal("29.00")
        assert invoice_draft.total_ttc == Decimal("219.00")

    def test_invoice_decimal_precision(self, invoice_draft):
        """Les calculs doivent respecter la précision décimale (arrondi ROUND_HALF_UP)."""
        # Arrange
        InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item décimal",
            quantity=3,
            unit_price=Decimal("33.33"),
            tax_rate=Decimal("20.00")
        )
        
        # Act
        invoice_draft.compute_totals()
        
        # Assert
        # 3 * 33.33 = 99.99 HT
        # 99.99 * 0.20 = 19.998 → arrondi à 20.00 TVA
        # TTC = 99.99 + 20.00 = 119.99
        assert invoice_draft.total_ht == Decimal("99.99")
        assert invoice_draft.tva == Decimal("20.00")
        assert invoice_draft.total_ttc == Decimal("119.99")


class TestInvoiceItemCalculations:
    """Tests des calculs au niveau des items de facture."""

    def test_invoice_item_total_ht(self, invoice_draft):
        """InvoiceItem.total_ht doit calculer quantity * unit_price."""
        # Arrange
        item = InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item",
            quantity=5,
            unit_price=Decimal("12.50"),
            tax_rate=Decimal("20.00")
        )
        
        # Assert
        assert item.total_ht == Decimal("62.50")

    def test_invoice_item_total_tva(self, invoice_draft):
        """InvoiceItem.total_tva doit calculer (total_ht * tax_rate / 100)."""
        # Arrange
        item = InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item",
            quantity=1,
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("20.00")
        )
        
        # Assert
        assert item.total_tva == Decimal("20.00")

    def test_invoice_item_total_ttc(self, invoice_draft):
        """InvoiceItem.total_ttc doit calculer total_ht + total_tva."""
        # Arrange
        item = InvoiceItem.objects.create(
            invoice=invoice_draft,
            description="Item",
            quantity=2,
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("10.00")
        )
        
        # Assert
        # HT: 2 * 50 = 100
        # TVA: 100 * 0.10 = 10
        # TTC: 100 + 10 = 110
        assert item.total_ttc == Decimal("110.00")


class TestInvoiceStatusTransitions:
    """Tests des transitions de statut des factures."""

    def test_invoice_can_change_status_draft_to_sent(self, invoice_draft):
        """Transition DRAFT → SENT autorisée."""
        # Act
        invoice_draft.status = Invoice.InvoiceStatus.SENT
        invoice_draft.save()
        
        # Assert
        assert invoice_draft.status == Invoice.InvoiceStatus.SENT

    def test_invoice_can_change_status_sent_to_paid(self, invoice_draft):
        """Transition SENT → PAID autorisée."""
        # Arrange
        invoice_draft.status = Invoice.InvoiceStatus.SENT
        invoice_draft.save()
        
        # Act
        invoice_draft.status = Invoice.InvoiceStatus.PAID
        invoice_draft.save()
        
        # Assert
        assert invoice_draft.status == Invoice.InvoiceStatus.PAID


class TestInvoiceQuoteLink:
    """Tests du lien facture ↔ devis."""

    def test_invoice_from_quote_has_correct_link(self, quote_accepted):
        """Une facture créée depuis un devis doit avoir le lien correct."""
        # Act
        result = create_invoice_from_quote(quote_accepted)
        
        # Assert
        assert result.invoice.quote == quote_accepted
        assert quote_accepted in [inv.quote for inv in Invoice.objects.all()]

    def test_quote_invoices_relation(self, quote_accepted):
        """Le devis doit avoir accès à ses factures via .invoices."""
        # Arrange
        result = create_invoice_from_quote(quote_accepted)
        
        # Act
        invoices = quote_accepted.invoices.all()
        
        # Assert
        assert invoices.count() == 1
        assert result.invoice in invoices


class TestInvoiceAmountLetter:
    """Tests de conversion montant en lettres."""

    def test_invoice_amount_letter_conversion(self, invoice_with_items):
        """Le montant doit être converti en lettres."""
        # Act
        amount_text = invoice_with_items.amount_letter()
        
        # Assert
        assert isinstance(amount_text, str)
        assert "euros" in amount_text.lower()
        assert len(amount_text) > 0


class TestInvoiceTransactionAtomicity:
    """Tests d'atomicité des transactions."""

    def test_conversion_is_atomic(self, quote_accepted, monkeypatch):
        """En cas d'erreur, la conversion doit être rollback complète."""
        # Arrange - Mock une erreur lors de la création des items
        original_create = InvoiceItem.objects.create
        call_count = [0]
        
        def failing_create(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # Première ligne OK
                return original_create(*args, **kwargs)
            else:  # Deuxième ligne fail
                raise Exception("Erreur simulée")
        
        monkeypatch.setattr(InvoiceItem.objects, 'create', failing_create)
        
        # Act & Assert
        initial_invoice_count = Invoice.objects.count()
        with pytest.raises(Exception, match="Erreur simulée"):
            create_invoice_from_quote(quote_accepted)
        
        # Vérifier qu'aucune facture n'a été créée (rollback)
        assert Invoice.objects.count() == initial_invoice_count
        # Le statut du devis n'a pas changé
        quote_accepted.refresh_from_db()
        assert quote_accepted.status == Quote.QuoteStatus.ACCEPTED

