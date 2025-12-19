"""
Port definitions for the hexagonal architecture.

These interfaces define the contracts that the domain logic depends on.
Concrete implementations live in the ``django_orm`` and ``weasyprint``
packages.  The goal of ports is to invert dependencies so that the
domain layer is completely decoupled from frameworks like Django or
third‑party libraries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

# Import Invoice entity from the sibling ``domain`` package.  The
# relative import uses two leading dots because this module is in
# ``hexcore/ports`` and the entities live in ``hexcore/domain``.
from ..domain.entities import Invoice  # type: ignore  # for type checking


class InvoiceRepository(ABC):
    """Repository interface for persisting and retrieving invoices."""

    @abstractmethod
    def create_from_quote(self, quote_id: int) -> Invoice:
        """Create a new invoice from the quote identified by ``quote_id``."""

    @abstractmethod
    def get(self, invoice_id: int) -> Invoice:
        """Retrieve an existing invoice from persistence."""

    @abstractmethod
    def save(self, invoice: Invoice) -> Invoice:
        """Persist modifications to an invoice back to storage."""

    @abstractmethod
    def attach_pdf(self, invoice_id: int, pdf_bytes: bytes, filename: str) -> None:
        """Attach a generated PDF to the invoice identified by ``invoice_id``."""


class PdfGenerator(ABC):
    """Interface for converting invoices into PDF documents."""

    @abstractmethod
    def generate(self, invoice: Invoice, *, branding: dict, extra_context: Optional[dict] = None) -> bytes:
        """Render the given invoice into PDF bytes."""