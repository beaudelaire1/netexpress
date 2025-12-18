from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.template.loader import render_to_string

try:
    from weasyprint import HTML
except Exception:  # pragma: no cover
    HTML = None  # type: ignore


@dataclass(frozen=True)
class PdfFile:
    filename: str
    content: bytes


def _branding() -> Dict[str, Any]:
    # Centralise branding for PDFs (invoice + quote)
    return getattr(settings, "INVOICE_BRANDING", {}) or {}


def render_quote_pdf(quote: Any, *, extra_context: Optional[Dict[str, Any]] = None) -> PdfFile:
    """Render a quote (devis) to premium PDF bytes using WeasyPrint."""
    if HTML is None:
        raise RuntimeError("WeasyPrint must be installed in order to generate PDFs.")

    # Build a context compatible with the premium invoice layout so that
    # the quote PDF can share the *exact* same design language.
    branding = _branding()

    # Rows: align with InvoicePdfService contract
    rows: list = []
    items_mgr = getattr(quote, "quote_items", None)
    for it in items_mgr.all() if items_mgr is not None else []:  # type: ignore[attr-defined]
        try:
            qty = getattr(it, "quantity", 0)
            pu = getattr(it, "unit_price", 0)
            total_ht_line = qty * pu
        except Exception:
            qty = 0
            pu = 0
            total_ht_line = 0
        # Prefer a clean, explicit description
        description = getattr(it, "description", "")
        srv = getattr(it, "service", None)
        if srv is not None and not description:
            description = getattr(srv, "name", None) or getattr(srv, "title", None) or str(srv)
        rows.append({
            "description": description,
            "quantity": qty,
            "unit_price": pu,
            "total_ht": total_ht_line,
        })

    total_ht_val = getattr(quote, "total_ht", 0) or 0
    total_tva_val = getattr(quote, "tva", 0) or 0
    try:
        tva_rate = (total_tva_val / total_ht_val) * 100 if total_ht_val else 0
    except Exception:
        tva_rate = 0

    client = getattr(quote, "client", None)
    client_name = getattr(client, "full_name", "") if client is not None else ""
    parts = []
    if client is not None:
        street = getattr(client, "address_line", None) or getattr(client, "address", None)
        if street:
            parts.append(str(street))
        zip_code = getattr(client, "zip_code", None)
        city = getattr(client, "city", None)
        if zip_code:
            parts.append(str(zip_code))
        if city:
            parts.append(str(city))
    client_address = "\n".join(parts) if parts else None
    client_email = getattr(client, "email", "") if client is not None else ""
    client_phone = getattr(client, "phone", "") if client is not None else ""
    client_reference = getattr(client, "reference", "") if client is not None else ""

    ctx: Dict[str, Any] = {
        "quote": quote,
        "branding": branding,
        "rows": rows,
        "tva_rate": tva_rate,
        "client_name": client_name,
        "client_address": client_address,
        "client_email": client_email,
        "client_phone": client_phone,
        "client_reference": client_reference,
    }

    if extra_context:
        ctx.update(extra_context)

    html = render_to_string("pdf/quote_premium.html", ctx)
    pdf_bytes = HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()
    number = getattr(quote, "number", None) or f"DEV-{getattr(quote, 'pk', 'X')}"
    filename = f"{number}.pdf"
    return PdfFile(filename=filename, content=pdf_bytes)


def generate_quote_pdf(quote: Any, context: Optional[Dict[str, Any]] = None) -> str:
    """Backward-compatible helper: write quote PDF to MEDIA_ROOT and return relative path."""
    pdf_res = render_quote_pdf(quote, extra_context=context or {})
    out_dir = Path(settings.MEDIA_ROOT) / "devis" / "pdf"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / pdf_res.filename
    out_path.write_bytes(pdf_res.content)
    # return relative media path suitable for FileField.name
    return f"devis/pdf/{pdf_res.filename}"
