"""
Concrete implementation of the InvoiceRepository using the Django ORM.

This adapter bridges the gap between the domain layer and the
framework.  It relies on existing Django models from the ``factures``
and ``devis`` apps to persist invoices and copy data from quotes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.core.files.base import ContentFile

from factures.models import Invoice as InvoiceModel, InvoiceItem as InvoiceItemModel
from devis.models import Quote, QuoteItem, Client
from devis.services import create_invoice_from_quote

from hexcore.domain.entities import Invoice, InvoiceItem
from hexcore.ports.interfaces import InvoiceRepository


class DjangoInvoiceRepository(InvoiceRepository):
    """Invoice repository backed by Django models."""

    def _to_entity(self, invoice_model: InvoiceModel) -> Invoice:
        """Convert a Django Invoice instance into a domain entity."""
        # Build line item entities
        items = []
        for it in invoice_model.invoice_items.all():
            items.append(
                InvoiceItem(
                    description=it.description or "",
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    tax_rate=it.tax_rate,
                )
            )
        # Extract client information if available
        client_name: Optional[str] = None
        client_address: Optional[str] = None
        client_email: Optional[str] = None
        client_phone: Optional[str] = None
        if invoice_model.quote and invoice_model.quote.client:
            client: Client = invoice_model.quote.client
            client_name = client.full_name
            # Compose a single address line (avoid blank values)
            parts = [client.address_line, client.zip_code, client.city]
            client_address = ", ".join([p for p in parts if p]) or None
            client_email = client.email or None
            client_phone = client.phone or None
        # Instantiate the domain entity
        entity = Invoice(
            number=invoice_model.number,
            issue_date=invoice_model.issue_date,
            due_date=invoice_model.due_date,
            status=invoice_model.status,
            discount=invoice_model.discount or Decimal("0.00"),
            notes=invoice_model.notes or "",
            payment_terms=invoice_model.payment_terms or "",
            items=items,
            client_name=client_name,
            client_address=client_address,
            client_email=client_email,
            client_phone=client_phone,
        )
        # Compute totals based on items and discount
        entity.compute_totals()
        return entity

    def create_from_quote(self, quote_id: int) -> Invoice:
        """Copy a quote into a new invoice and return the domain entity.

        This implementation leverages the existing ``devis.services.create_invoice_from_quote``
        function to perform the necessary checks (quote status, duplication) and
        to create the underlying Invoice and InvoiceItem models within a
        transaction.  After creation, the invoice model is converted
        into a domain entity.  If any exception occurs during
        creation, it is propagated to the caller.
        """
        # Use the service to create the invoice in the database
        result = create_invoice_from_quote(quote_id)
        invoice_model = result.invoice
        # Prefetch items for conversion
        invoice_model = InvoiceModel.objects.select_related("quote__client").prefetch_related("invoice_items").get(pk=invoice_model.pk)
        return self._to_entity(invoice_model)

    def get(self, invoice_id: int) -> Invoice:
        """Retrieve an invoice by primary key and return the domain entity."""
        invoice_model = InvoiceModel.objects.select_related("quote__client").prefetch_related("invoice_items").get(pk=invoice_id)
        return self._to_entity(invoice_model)

    def save(self, invoice: Invoice) -> Invoice:
        """Persist modifications to an existing invoice.

        The invoice is looked up by its number.  Totals, notes and
        payment terms are written back to the corresponding model.
        Additional attributes (like status or due_date) can also be
        persisted if needed.  This method returns the domain invoice
        unchanged for convenience.
        """
        try:
            invoice_model = InvoiceModel.objects.get(number=invoice.number)
        except InvoiceModel.DoesNotExist:
            # If the invoice does not exist, nothing to persist
            return invoice
        # Update fields
        invoice_model.total_ht = invoice.total_ht
        invoice_model.tva = invoice.total_tva
        invoice_model.total_ttc = invoice.total_ttc
        invoice_model.notes = invoice.notes
        invoice_model.payment_terms = invoice.payment_terms
        invoice_model.discount = invoice.discount
        # Persist
        invoice_model.save(update_fields=[
            "total_ht", "tva", "total_ttc", "notes", "payment_terms", "discount"
        ])
        return invoice

    def attach_pdf(self, invoice_id: int, pdf_bytes: bytes, filename: str) -> None:
        """Save a PDF document to the invoice's FileField."""
        invoice_model = InvoiceModel.objects.get(pk=invoice_id)
        # Use ContentFile to wrap bytes for Django FileField
        invoice_model.pdf.save(filename, ContentFile(pdf_bytes), save=True)