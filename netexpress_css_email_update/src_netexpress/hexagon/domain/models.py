"""Domain entities for NetExpress.

This module defines pure Python representations of the core business
entities used throughout NetExpress.  These classes are designed to
mirror the shape of the corresponding Django models without exposing
any framework‑specific details.  They provide type hints and simple
methods that encapsulate business rules, making them suitable for use
in unit tests and application services.

The current definitions are intentionally conservative: they implement
only a subset of the fields exposed by the Django models.  When
building new features, prefer using these domain entities rather than
directly depending on Django models.  Over time, existing logic can
be extracted from the models into the domain layer.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

@dataclass
class Service:
    """A service offered by NetExpress.

    :param name: Human‑friendly name of the service
    :param description: Short description for display in the catalogue
    :param price: Price excluding taxes for the service
    """
    name: str
    description: str
    price: Decimal

@dataclass
class QuoteItem:
    """An item within a quote.

    Quote items reference a service or describe a custom line.  The
    total amounts are computed lazily from the unit price, quantity
    and tax rate.

    :param description: Description of the line item
    :param quantity: Quantity ordered
    :param unit_price: Unit price (pre‑tax)
    :param tax_rate: Tax rate as a fraction (e.g. 0.2 for 20 %)
    """
    description: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal

    @property
    def total_ht(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_tva(self) -> Decimal:
        return (self.total_ht * self.tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_ttc(self) -> Decimal:
        return (self.total_ht + self.total_tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

@dataclass
class Quote:
    """A business quote for services.

    Quotes aggregate multiple items and maintain aggregated totals.  In
    the Django application a quote is persisted with a number and a
    status; here we focus on the monetary logic.  The ``valid_until``
    field defaults to 30 days after the issue date.  The totals are
    computed via :meth:`compute_totals`.
    """
    client_name: str
    items: List[QuoteItem] = field(default_factory=list)
    issue_date: date = field(default_factory=date.today)
    valid_until: date = field(default_factory=lambda: date.today() + timedelta(days=30))
    total_ht: Decimal = Decimal("0.00")
    tva: Decimal = Decimal("0.00")
    total_ttc: Decimal = Decimal("0.00")

    def compute_totals(self) -> None:
        total_ht = sum((item.total_ht for item in self.items), start=Decimal("0.00"))
        total_tva = sum((item.total_tva for item in self.items), start=Decimal("0.00"))
        self.total_ht = total_ht.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.tva = total_tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.total_ttc = (self.total_ht + self.tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

@dataclass
class Task:
    """A task assigned to an employee.

    Tasks have a title, a description, start and due dates, and a flag
    indicating whether they have been completed.  The domain model
    provides utility methods for computing overdue status and the
    remaining duration.
    """
    title: str
    description: str
    start_date: date
    due_date: date
    completed: bool = False

    def is_overdue(self, today: Optional[date] = None) -> bool:
        """Return ``True`` if the task due date has passed and it is not completed."""
        today = today or date.today()
        return not self.completed and self.due_date < today

    def days_remaining(self, today: Optional[date] = None) -> int:
        """Return the number of days until the due date.  Negative if overdue."""
        today = today or date.today()
        return (self.due_date - today).days