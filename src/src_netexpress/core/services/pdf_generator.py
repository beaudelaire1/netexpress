"""
Génération des documents PDF NetExpress via WeasyPrint.

Le devis est rendu directement ici. La facture délègue à InvoicePdfService afin
qu'il n'existe qu'une seule préparation du contexte facture dans l'application.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.template.loader import render_to_string

try:
    from weasyprint import HTML, CSS  # type: ignore
except Exception:  # pragma: no cover
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


def render_quote_pdf(
    quote,
    *,
    extra_context: Optional[Dict[str, Any]] = None,
) -> PDFRenderResult:
    if HTML is None:
        raise PDFGeneratorError(
            "WeasyPrint n'est pas disponible. Installez weasyprint et ses dépendances système."
        )

    context: Dict[str, Any] = {
        "doc_type": "quote",
        "quote": quote,
        "branding": _branding(),
    }
    if extra_context:
        context.update(extra_context)

    html = render_to_string("pdf/quote.html", context)
    base_url = str(getattr(settings, "BASE_DIR", Path.cwd()))

    css_path = Path(base_url) / "static" / "css" / "pdf.css"
    stylesheets = []
    if css_path.exists() and CSS is not None:
        stylesheets.append(CSS(filename=str(css_path)))

    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf(stylesheets=stylesheets)
    number = getattr(quote, "number", None) or f"DEV-{getattr(quote, 'pk', 'X')}"
    return PDFRenderResult(filename=f"{number}.pdf", content=pdf_bytes)


def render_invoice_pdf(
    invoice,
    *,
    extra_context: Optional[Dict[str, Any]] = None,
) -> PDFRenderResult:
    """Point d'entrée compatible vers l'unique service de rendu facture."""

    from core.services.pdf_service import InvoicePdfService

    try:
        result = InvoicePdfService().generate(invoice, extra_context=extra_context)
    except RuntimeError as exc:
        raise PDFGeneratorError(str(exc)) from exc

    return PDFRenderResult(
        filename=result.filename,
        content=result.content,
        mimetype=result.mimetype,
    )
