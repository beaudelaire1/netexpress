"""
Services de génération PDF pour les devis et factures NetExpress.

La couche métier reste dans les modèles. Ce module prépare uniquement le
contexte de rendu et délègue la conversion HTML -> PDF à WeasyPrint.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

try:
    from weasyprint import HTML, CSS  # type: ignore
except ImportError:  # pragma: no cover
    HTML = None  # type: ignore
    CSS = None  # type: ignore


@dataclass
class PdfFile:
    """Conteneur minimal pour un document PDF généré."""

    filename: str
    content: bytes
    mimetype: str = "application/pdf"


def _as_decimal(value) -> Decimal:
    """Convertit une valeur numérique en Decimal sans propager d'erreur de rendu."""

    try:
        return Decimal(str(value or 0))
    except (TypeError, ValueError, ArithmeticError):
        return Decimal("0.00")


class InvoicePdfService:
    """Génère les factures depuis le template premium NetExpress."""

    template_name: str = "pdf/invoice_premium.html"

    def generate(self, invoice) -> PdfFile:
        if HTML is None:
            raise RuntimeError(
                "WeasyPrint doit être installé pour générer les factures PDF."
            )

        branding = dict(getattr(settings, "INVOICE_BRANDING", {}) or {})

        rows: list[dict] = []
        inv_items = getattr(invoice, "invoice_items", None)
        items = inv_items.all() if inv_items is not None else []  # type: ignore[attr-defined]
        for item in items:
            quantity = _as_decimal(getattr(item, "quantity", 0))
            unit_price = _as_decimal(getattr(item, "unit_price", 0))
            tax_rate = _as_decimal(getattr(item, "tax_rate", 0))

            total_ht = _as_decimal(getattr(item, "total_ht", quantity * unit_price))
            total_tva = _as_decimal(
                getattr(item, "total_tva", total_ht * tax_rate / Decimal("100"))
            )
            total_ttc = _as_decimal(getattr(item, "total_ttc", total_ht + total_tva))

            rows.append(
                {
                    "description": getattr(item, "description", "") or "Prestation",
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "tax_rate": tax_rate,
                    "total_ht": total_ht,
                    "total_tva": total_tva,
                    "total_ttc": total_ttc,
                }
            )

        total_ht_value = _as_decimal(getattr(invoice, "total_ht", 0))
        total_tva_value = _as_decimal(getattr(invoice, "tva", 0))
        tva_rate = (
            (total_tva_value / total_ht_value) * Decimal("100")
            if total_ht_value
            else Decimal("0.00")
        )

        client_name = ""
        client_company = ""
        client_address: str | None = None
        client_email = ""
        client_phone = ""
        client_reference = ""

        quote = getattr(invoice, "quote", None)
        client = getattr(quote, "client", None) if quote is not None else None
        if client is not None:
            client_name = getattr(client, "full_name", "") or ""
            client_company = getattr(client, "company", "") or ""

            address_parts: list[str] = []
            street = getattr(client, "address_line", None) or getattr(client, "address", None)
            if street:
                address_parts.append(str(street))
            city_line = " ".join(
                part
                for part in (
                    str(getattr(client, "zip_code", "") or "").strip(),
                    str(getattr(client, "city", "") or "").strip(),
                )
                if part
            )
            if city_line:
                address_parts.append(city_line)
            if address_parts:
                client_address = "\n".join(address_parts)

            client_email = getattr(client, "email", "") or ""
            client_phone = getattr(client, "phone", "") or ""
            client_reference = getattr(client, "reference", "") or ""

        context = {
            "invoice": invoice,
            "branding": branding,
            "rows": rows,
            # Conservé pour compatibilité avec d'éventuels templates secondaires.
            "tva_rate": tva_rate,
            "client_name": client_name,
            "client_company": client_company,
            "client_address": client_address,
            "client_email": client_email,
            "client_phone": client_phone,
            "client_reference": client_reference,
        }

        html_string = render_to_string(self.template_name, context)
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        stylesheets = []
        css_path = base_dir / "static" / "css" / "pdf.css"
        if css_path.exists() and CSS is not None:
            stylesheets.append(CSS(filename=str(css_path)))

        pdf_bytes = HTML(string=html_string, base_url=str(base_dir)).write_pdf(
            stylesheets=stylesheets
        )
        number = getattr(invoice, "number", None) or f"FAC-{getattr(invoice, 'pk', 'X')}"
        return PdfFile(filename=f"{number}.pdf", content=pdf_bytes)


class QuotePdfService:
    """Génère un devis via le renderer WeasyPrint partagé."""

    def generate(self, quote) -> PdfFile:
        from core.services.pdf_generator import render_quote_pdf

        result = render_quote_pdf(quote)
        return PdfFile(
            filename=result.filename,
            content=result.content,
            mimetype=result.mimetype,
        )
