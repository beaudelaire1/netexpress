from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

try:
    from weasyprint import CSS, HTML, default_url_fetcher
except (ImportError, OSError):  # pragma: no cover - dépendance système
    CSS = None
    HTML = None
    default_url_fetcher = None

logger = logging.getLogger(__name__)


def restricted_fetcher(url, *args, **kwargs):
    """Autorise uniquement les ressources PDF locales du projet."""
    if default_url_fetcher is None:
        raise RuntimeError("WeasyPrint n'est pas installé.")

    from urllib.parse import unquote, urlparse
    from urllib.request import url2pathname

    parsed = urlparse(url)
    if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
        raise ValueError("Ressource PDF distante interdite")

    path = Path(url2pathname(unquote(parsed.path))).resolve()
    roots = [Path(settings.BASE_DIR) / "static"]
    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:
        roots.append(Path(static_root))

    if not any(path.is_relative_to(root.resolve()) for root in roots):
        raise ValueError("Ressource PDF hors du répertoire statique")

    return default_url_fetcher(path.as_uri())


@dataclass(frozen=True)
class PdfFile:
    filename: str
    content: bytes
    mimetype: str = "application/pdf"


class DocumentGenerator:
    """Générateur WeasyPrint commun aux devis et factures NetExpress."""

    @staticmethod
    def _get_branding() -> Dict[str, Any]:
        return dict(getattr(settings, "INVOICE_BRANDING", {}) or {})

    @staticmethod
    def _as_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0.00")

    @classmethod
    def _get_client_info(cls, obj: Any) -> Dict[str, str]:
        """Extrait les informations client sans dépendre d'un modèle précis."""
        client = getattr(obj, "client", None)
        if client is None:
            quote = getattr(obj, "quote", None)
            client = getattr(quote, "client", None) if quote else None

        info = {
            "name": "",
            "company": "",
            "address": "",
            "email": "",
            "phone": "",
            "reference": "",
        }
        if client is None:
            return info

        info["name"] = str(getattr(client, "full_name", "") or "")
        info["company"] = str(getattr(client, "company", "") or "")
        info["email"] = str(getattr(client, "email", "") or "")
        info["phone"] = str(getattr(client, "phone", "") or "")
        info["reference"] = str(getattr(client, "reference", "") or "")

        address_lines = []
        street = getattr(client, "address_line", None) or getattr(client, "address", None)
        if street:
            address_lines.append(str(street))

        locality = " ".join(
            part
            for part in (
                str(getattr(client, "zip_code", "") or "").strip(),
                str(getattr(client, "city", "") or "").strip(),
            )
            if part
        )
        if locality:
            address_lines.append(locality)

        info["address"] = "\n".join(address_lines)
        return info

    @classmethod
    def _get_rows(cls, obj: Any) -> list[Dict[str, Any]]:
        """Normalise les lignes de devis/facture pour les templates PDF."""
        items_manager = getattr(obj, "quote_items", None)
        if items_manager is None:
            items_manager = getattr(obj, "invoice_items", None)
        items = items_manager.all() if items_manager is not None else []

        rows: list[Dict[str, Any]] = []
        for item in items:
            quantity = cls._as_decimal(getattr(item, "quantity", 0))
            unit_price = cls._as_decimal(getattr(item, "unit_price", 0))
            tax_rate = cls._as_decimal(getattr(item, "tax_rate", 0))

            calculated_ht = (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_ht = cls._as_decimal(getattr(item, "total_ht", calculated_ht))
            total_tva = cls._as_decimal(
                getattr(
                    item,
                    "total_tva",
                    (total_ht * tax_rate / Decimal("100")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    ),
                )
            )
            total_ttc = cls._as_decimal(getattr(item, "total_ttc", total_ht + total_tva))

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
        return rows

    @classmethod
    def _build_context(cls, obj: Any, prefix: str) -> Dict[str, Any]:
        client = cls._get_client_info(obj)
        rows = cls._get_rows(obj)

        total_ht = cls._as_decimal(getattr(obj, "total_ht", 0))
        total_tva = cls._as_decimal(getattr(obj, "tva", 0))
        tva_rate = (
            (total_tva / total_ht * Decimal("100")).quantize(Decimal("0.01"))
            if total_ht
            else Decimal("0.00")
        )

        context: Dict[str, Any] = {
            "object": obj,
            "branding": cls._get_branding(),
            "rows": rows,
            "tva_rate": tva_rate,
            "client_name": client["name"],
            "client_company": client["company"],
            "client_address": client["address"],
            "client_email": client["email"],
            "client_phone": client["phone"],
            "client_reference": client["reference"],
        }
        context["quote" if prefix == "DEV" else "invoice"] = obj
        return context

    @classmethod
    def generate_pdf(cls, obj: Any, template_name: str, prefix: str = "DOC") -> PdfFile:
        if HTML is None:
            raise RuntimeError("WeasyPrint n'est pas installé.")

        html_string = render_to_string(template_name, cls._build_context(obj, prefix))
        base_dir = Path(settings.BASE_DIR)

        stylesheets = []
        for stylesheet_name in ("css/pdf.css", "css/pdf-layout-fixes.css"):
            css_path = finders.find(stylesheet_name)
            if css_path is None:
                static_root = getattr(settings, "STATIC_ROOT", None)
                candidate = Path(static_root) / stylesheet_name if static_root else None
                if candidate and candidate.exists():
                    css_path = str(candidate)

            if css_path and CSS is not None:
                stylesheets.append(
                    CSS(filename=str(css_path), url_fetcher=restricted_fetcher)
                )

        pdf_bytes = HTML(
            string=html_string,
            base_url=str(base_dir),
            url_fetcher=restricted_fetcher,
        ).write_pdf(stylesheets=stylesheets)

        number = getattr(obj, "number", None) or f"{prefix}-{getattr(obj, 'pk', 'X')}"
        return PdfFile(filename=f"{number}.pdf", content=pdf_bytes)

    @classmethod
    def generate_quote_pdf(cls, quote: Any, attach: bool = True) -> bytes:
        pdf_file = cls.generate_pdf(quote, "pdf/quote_premium.html", "DEV")
        if attach and hasattr(quote, "pdf"):
            quote.pdf.save(pdf_file.filename, ContentFile(pdf_file.content), save=True)
        return pdf_file.content

    @classmethod
    def generate_invoice_pdf(cls, invoice: Any, attach: bool = True) -> bytes:
        pdf_file = cls.generate_pdf(invoice, "pdf/invoice_premium.html", "FAC")
        if attach and hasattr(invoice, "pdf"):
            invoice.pdf.save(pdf_file.filename, ContentFile(pdf_file.content), save=True)
        return pdf_file.content
