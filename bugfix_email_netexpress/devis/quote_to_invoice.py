"""Conversion Devis -> Facture.

API stable : QuoteToInvoiceService.convert(quote) -> Invoice
La logique est centralisée dans Quote.convert_to_invoice().
"""

from __future__ import annotations


class QuoteToInvoiceService:
    @staticmethod
    def convert(quote):
        return quote.convert_to_invoice()
