"""
Service layer for invoice creation and PDF generation.

The :class:`InvoiceService` orchestrates interactions between
repositories and adapters to fulfil use cases.  It coordinates the
creation of invoices from quotes, delegates persistence to a
repository and delegates document rendering to a PDF generator.  By
injecting its dependencies via the constructor, this service remains
testable and agnostic of concrete frameworks.
"""

from __future__ import annotations

from typing import Optional

from ..domain.entities import Invoice
from ..ports.interfaces import InvoiceRepository, PdfGenerator


class InvoiceService:
    """Application service for invoicing use cases."""

    def __init__(self, invoice_repository: InvoiceRepository, pdf_generator: PdfGenerator) -> None:
        self.invoice_repository = invoice_repository
        self.pdf_generator = pdf_generator

    def create_invoice_from_quote(self, quote_id: int) -> Invoice:
        """Create an invoice from an existing quote and persist it.

        The newly created invoice entity is computed for totals and
        saved back to the repository.  The returned entity reflects
        the latest persisted state.
        """
        invoice = self.invoice_repository.create_from_quote(quote_id)
        invoice.compute_totals()
        invoice = self.invoice_repository.save(invoice)
        return invoice

    def generate_invoice_pdf(
        self,
        invoice_id: int,
        *,
        branding: dict,
        extra_context: Optional[dict] = None,
        attach: bool = True,
    ) -> bytes:
        """Generate a PDF for the invoice identified by ``invoice_id``.

        The invoice is reloaded from the repository, totals are
        computed on the fly, then the generator is called.  If
        ``attach`` is true the resulting PDF is stored on the
        repository as a file.  The bytes of the PDF are returned in
        all cases.
        """
        invoice = self.invoice_repository.get(invoice_id)
        invoice.compute_totals()
        pdf_bytes = self.pdf_generator.generate(invoice, branding=branding, extra_context=extra_context)
        if attach:
            number = invoice.number or f"FAC-{invoice_id}"
            filename = f"{number}.pdf"
            self.invoice_repository.attach_pdf(invoice_id, pdf_bytes, filename)
        return pdf_bytes