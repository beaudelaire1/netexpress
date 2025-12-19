"""
Domain entities for the Netexpress invoicing module.

These dataclasses model an invoice and its line items independently
of any specific persistence or framework.  They encapsulate just the
data structure and simple computations required for invoices.  No
imports from Django or other frameworks are permitted in this module,
which makes it suitable for pure business logic and unit testing.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional


@dataclass
class InvoiceItem:
    """A single line item on an invoice."""

    description: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal

    @property
    def total_ht(self) -> Decimal:
        return (self.unit_price * Decimal(self.quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def total_tva(self) -> Decimal:
        return (
            self.total_ht * self.tax_rate / Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_ttc(self) -> Decimal:
        return (
            self.total_ht + self.total_tva
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class Invoice:
    """Domain representation of an invoice."""

    number: str
    issue_date: date
    due_date: Optional[date] = None
    status: str = "draft"
    discount: Decimal = Decimal("0.00")
    notes: str = ""
    payment_terms: str = ""
    items: List[InvoiceItem] = field(default_factory=list)

    client_name: Optional[str] = None
    client_address: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None

    total_ht: Decimal = Decimal("0.00")
    total_tva: Decimal = Decimal("0.00")
    total_ttc: Decimal = Decimal("0.00")

    def compute_totals(self) -> None:
        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")
        for item in self.items:
            total_ht += item.total_ht
            total_tva += item.total_tva
        discount = self.discount or Decimal("0.00")
        if discount > 0 and total_ht > 0:
            ratio = (discount / total_ht).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            total_ht -= discount
            total_tva -= (total_tva * ratio)
        if total_ht < 0:
            total_ht = Decimal("0.00")
        if total_tva < 0:
            total_tva = Decimal("0.00")
        self.total_ht = total_ht.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.total_tva = total_tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.total_ttc = (
            self.total_ht + self.total_tva
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)