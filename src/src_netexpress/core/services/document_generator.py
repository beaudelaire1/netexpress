from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List

from django.conf import settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

try:
    from weasyprint import HTML, CSS
except ImportError:
    HTML = None
    CSS = None

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class PdfFile:
    filename: str
    content: bytes
    mimetype: str = "application/pdf"

class DocumentGenerator:
    """
    Service unifié pour la génération de documents PDF (Devis et Factures).
    Centralise la logique WeasyPrint et le branding.
    """

    @staticmethod
    def _get_branding() -> Dict[str, Any]:
        return getattr(settings, "INVOICE_BRANDING", {}) or {}

    @staticmethod
    def _get_client_info(obj: Any) -> Dict[str, Any]:
        """Extrait les informations client d'un devis ou d'une facture."""
        client = None
        if hasattr(obj, "client"):
            client = obj.client
        elif hasattr(obj, "quote") and obj.quote and hasattr(obj.quote, "client"):
            client = obj.quote.client
        
        info = {
            "name": "",
            "address": "",
            "email": "",
            "phone": "",
            "reference": "",
        }

        if client:
            info["name"] = getattr(client, "full_name", "") or ""
            parts = []
            street = getattr(client, "address_line", None) or getattr(client, "address", None)
            if street: parts.append(str(street))
            zip_code = getattr(client, "zip_code", None)
            city = getattr(client, "city", None)
            if zip_code: parts.append(str(zip_code))
            if city: parts.append(str(city))
            info["address"] = "\n".join(parts)
            info["email"] = getattr(client, "email", "") or ""
            info["phone"] = getattr(client, "phone", "") or ""
            info["reference"] = getattr(client, "reference", "") or ""
        
        return info

    @classmethod
    def generate_pdf(cls, obj: Any, template_name: str, prefix: str = "DOC") -> PdfFile:
        """Générateur générique de PDF."""
        if HTML is None:
            raise RuntimeError("WeasyPrint n'est pas installé.")

        branding = cls._get_branding()
        client_info = cls._get_client_info(obj)

        # Préparation des lignes (rows)
        rows = []
        items_mgr = None
        if hasattr(obj, "quote_items"):
            items_mgr = obj.quote_items
        elif hasattr(obj, "invoice_items"):
            items_mgr = obj.invoice_items
        
        for it in items_mgr.all() if items_mgr else []:
            qty = getattr(it, "quantity", 0)
            pu = getattr(it, "unit_price", 0)
            rows.append({
                "description": getattr(it, "description", ""),
                "quantity": qty,
                "unit_price": pu,
                "total_ht": qty * pu,
            })

        # Calcul du taux de TVA moyen pour l'affichage
        total_ht = getattr(obj, "total_ht", 0) or 0
        total_tva = getattr(obj, "tva", 0) or 0
        tva_rate = (total_tva / total_ht * 100) if total_ht else 0

        context = {
            "object": obj,
            "branding": branding,
            "rows": rows,
            "tva_rate": tva_rate,
            "client_name": client_info["name"],
            "client_address": client_info["address"],
            "client_email": client_info["email"],
            "client_phone": client_info["phone"],
            "client_reference": client_info["reference"],
        }

        # Ajout des alias pour la compatibilité des templates
        if prefix == "DEV":
            context["quote"] = obj
        else:
            context["invoice"] = obj

        html_string = render_to_string(template_name, context)
        base_dir = Path(settings.BASE_DIR)
        
        stylesheets = []
        css_path = base_dir / "static" / "css" / "pdf.css"
        if css_path.exists() and CSS is not None:
            stylesheets.append(CSS(filename=str(css_path)))

        pdf_bytes = HTML(string=html_string, base_url=str(base_dir)).write_pdf(stylesheets=stylesheets)
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

