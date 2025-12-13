from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class InvoiceLine:
  description: str
  quantity: Decimal
  unit_price_ht: Decimal
  vat_rate: Decimal

  @property
  def total_ht(self) -> Decimal:
    return (self.quantity * self.unit_price_ht).quantize(Decimal("0.01"))

  @property
  def total_ttc(self) -> Decimal:
    factor = Decimal("1") + self.vat_rate / Decimal("100")
    return (self.total_ht * factor).quantize(Decimal("0.01"))


@dataclass
class InvoiceAggregate:
  number: str
  customer_label: str
  lines: List[InvoiceLine]

  @property
  def total_ht(self) -> Decimal:
    return sum((l.total_ht for l in self.lines), Decimal("0.00"))

  @property
  def total_ttc(self) -> Decimal:
    return sum((l.total_ttc for l in self.lines), Decimal("0.00"))
