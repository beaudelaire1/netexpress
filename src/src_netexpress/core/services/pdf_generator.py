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
    """Retourne les informations de branding avec résolution du logo."""
    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
    return branding


def _resolve_logo_for_weasyprint(logo_path: Optional[str]) -> Optional[str]:
    """Résout le chemin du logo pour WeasyPrint.

    WeasyPrint a besoin d'un chemin absolu ou d'une URL file://
    pour pouvoir charger les images locales.
    """
    if not logo_path:
        return None

    import os

    # Si c'est déjà un chemin absolu existant
    if os.path.isabs(logo_path) and os.path.exists(logo_path):
        return logo_path

    # Essayer de résoudre via staticfiles
    try:
        from django.contrib.staticfiles import finders
        # Nettoyer le préfixe "static:" si présent
        rel_path = logo_path.replace("static:", "").lstrip("/\\")
        resolved = finders.find(rel_path)
        if resolved and os.path.exists(resolved):
            return resolved
    except Exception:
        pass

    # Fallback: chercher dans STATIC_ROOT ou BASE_DIR/static
    base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    candidates = [
        base_dir / "static" / logo_path.lstrip("/\\"),
        base_dir / "staticfiles" / logo_path.lstrip("/\\"),
        Path(logo_path),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def render_quote_pdf(quote, *, extra_context: Optional[Dict[str, Any]] = None) -> PDFRenderResult:
    if HTML is None:
        raise PDFGeneratorError("WeasyPrint n'est pas disponible. Installez weasyprint et ses dépendances système.")

    # Préparer le branding avec résolution du logo
    branding = _branding().copy()
    logo_path = branding.get("logo_path")
    if logo_path:
        resolved_logo = _resolve_logo_for_weasyprint(logo_path)
        if resolved_logo:
            branding["logo_path"] = resolved_logo

    ctx: Dict[str, Any] = {
        "doc_type": "quote",
        "quote": quote,
        "branding": branding,
    }
    if extra_context:
        ctx.update(extra_context)

    html = render_to_string("pdf/quote.html", ctx)
    base_url = str(getattr(settings, "BASE_DIR", Path.cwd()))

    css_path = Path(base_url) / "static" / "css" / "pdf.css"
    stylesheets = []
    if css_path.exists():
        stylesheets.append(CSS(filename=str(css_path)))

    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf(stylesheets=stylesheets)

    number = getattr(quote, "number", None) or f"DEV-{getattr(quote, 'pk', 'X')}"
    return PDFRenderResult(filename=f"{number}.pdf", content=pdf_bytes)


def render_invoice_pdf(invoice, *, extra_context: Optional[Dict[str, Any]] = None) -> PDFRenderResult:
    if HTML is None:
        raise PDFGeneratorError("WeasyPrint n'est pas disponible. Installez weasyprint et ses dépendances système.")

    # Préparer le branding avec résolution du logo
    branding = _branding().copy()
    logo_path = branding.get("logo_path")
    if logo_path:
        resolved_logo = _resolve_logo_for_weasyprint(logo_path)
        if resolved_logo:
            branding["logo_path"] = resolved_logo

    ctx: Dict[str, Any] = {
        "doc_type": "invoice",
        "invoice": invoice,
        "branding": branding,
    }
    if extra_context:
        ctx.update(extra_context)

    html = render_to_string("pdf/invoice_premium.html", ctx)
    base_url = str(getattr(settings, "BASE_DIR", Path.cwd()))

    css_path = Path(base_url) / "static" / "css" / "pdf.css"
    stylesheets = []
    if css_path.exists():
        stylesheets.append(CSS(filename=str(css_path)))

    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf(stylesheets=stylesheets)

    number = getattr(invoice, "number", None) or f"FAC-{getattr(invoice, 'pk', 'X')}"
    return PDFRenderResult(filename=f"{number}.pdf", content=pdf_bytes)
