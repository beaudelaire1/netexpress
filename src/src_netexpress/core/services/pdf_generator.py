"""
core/services/pdf_generator.py

Génération de documents PDF premium (Devis / Facture) via WeasyPrint.

Objectifs :
- Rendu "document officiel" (luxe B2B)
- Template HTML dédié (non dépendant du CSS web)
- Logo + coordonnées + tableau des prestations + totaux + conditions + IBAN/BIC
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.template.loader import render_to_string

try:
    from weasyprint import HTML, CSS  # type: ignore
except Exception as exc:  # pragma: no cover
    HTML = None  # type: ignore
    CSS = None  # type: ignore


@dataclass(frozen=True)
class PDFRenderResult:
    filename: str
    content: bytes
    mimetype: str = "application/pdf"


class PDFGeneratorError(RuntimeError):
    pass


def _branding() -> Dict[str, Any]:
    return getattr(settings, "INVOICE_BRANDING", {}) or {}


def render_quote_pdf(quote, *, extra_context: Optional[Dict[str, Any]] = None) -> PDFRenderResult:
    if HTML is None:
        raise PDFGeneratorError("WeasyPrint n'est pas disponible. Installez weasyprint et ses dépendances système.")

    ctx: Dict[str, Any] = {
        "doc_type": "quote",
        "quote": quote,
        "branding": _branding(),
    }
    if extra_context:
        ctx.update(extra_context)

    html = render_to_string("pdf/quote.html", ctx)
    base_url = str(getattr(settings, "BASE_DIR", Path.cwd()))

    # Try to locate the CSS file using staticfiles finders (production-ready)
    css_path = None
    try:
        from django.contrib.staticfiles import finders
        css_path = finders.find("css/pdf.css")
    except Exception:
        pass
    # Fallback to STATIC_ROOT if finders don't work
    if not css_path:
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            candidate = Path(static_root) / "css" / "pdf.css"
            if candidate.exists():
                css_path = str(candidate)
    # Final fallback to BASE_DIR/static for development
    if not css_path:
        candidate = Path(base_url) / "static" / "css" / "pdf.css"
        if candidate.exists():
            css_path = str(candidate)
    
    stylesheets = []
    if css_path:
        stylesheets.append(CSS(filename=str(css_path)))

    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf(stylesheets=stylesheets)

    number = getattr(quote, "number", None) or f"DEV-{getattr(quote, 'pk', 'X')}"
    return PDFRenderResult(filename=f"{number}.pdf", content=pdf_bytes)


def render_invoice_pdf(invoice, *, extra_context: Optional[Dict[str, Any]] = None) -> PDFRenderResult:
    if HTML is None:
        raise PDFGeneratorError("WeasyPrint n'est pas disponible. Installez weasyprint et ses dépendances système.")

    ctx: Dict[str, Any] = {
        "doc_type": "invoice",
        "invoice": invoice,
        "branding": _branding(),
    }
    if extra_context:
        ctx.update(extra_context)

    html = render_to_string("pdf/invoice_premium.html", ctx)
    base_url = str(getattr(settings, "BASE_DIR", Path.cwd()))

    # Try to locate the CSS file using staticfiles finders (production-ready)
    css_path = None
    try:
        from django.contrib.staticfiles import finders
        css_path = finders.find("css/pdf.css")
    except Exception:
        pass
    # Fallback to STATIC_ROOT if finders don't work
    if not css_path:
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            candidate = Path(static_root) / "css" / "pdf.css"
            if candidate.exists():
                css_path = str(candidate)
    # Final fallback to BASE_DIR/static for development
    if not css_path:
        candidate = Path(base_url) / "static" / "css" / "pdf.css"
        if candidate.exists():
            css_path = str(candidate)
    
    stylesheets = []
    if css_path:
        stylesheets.append(CSS(filename=str(css_path)))

    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf(stylesheets=stylesheets)

    number = getattr(invoice, "number", None) or f"FAC-{getattr(invoice, 'pk', 'X')}"
    return PDFRenderResult(filename=f"{number}.pdf", content=pdf_bytes)
