"""Génération de PDF (Premium) via WeasyPrint.

Objectifs
---------
- Centraliser la génération des PDF (devis / documents HTML → PDF)
- Produire un rendu "luxe" basé sur un template HTML/CSS.

WeasyPrint est privilégié ici car il gère correctement les tableaux,
les polices et les règles @page.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string


def _get_branding() -> dict:
    """Normalise ``settings.INVOICE_BRANDING`` pour les documents."""
    cfg = getattr(settings, "INVOICE_BRANDING", {}) or {}
    addr_lines = cfg.get("address_lines")
    if not addr_lines:
        addr = cfg.get("address")
        if addr:
            addr_lines = [line.strip() for line in str(addr).splitlines() if line.strip()]
        else:
            addr_lines = []

    return {
        "name": cfg.get("name", "Nettoyage Express"),
        "tagline": cfg.get("tagline", ""),
        "email": cfg.get("email", ""),
        "phone": cfg.get("phone", ""),
        "website": cfg.get("website", ""),
        "address_lines": addr_lines,
        "siret": cfg.get("siret", ""),
        "tva_intra": cfg.get("tva_intra", ""),
        "iban": cfg.get("iban", ""),
        "bic": cfg.get("bic", ""),
        "logo_path": cfg.get("logo_path", None),
    }


def _resolve_logo_file_url(logo_path: Optional[str]) -> Optional[str]:
    """Retourne une URL de type ``file://`` exploitable par WeasyPrint.

    - Si le chemin est absolu et existe → utilisé.
    - Si le chemin est relatif → recherché dans STATICFILES_DIRS / STATIC_ROOT.
    """
    if not logo_path:
        return None

    try:
        p = Path(logo_path)
        if p.is_absolute() and p.exists():
            return p.resolve().as_uri()

        rel = str(logo_path).replace("static:", "").lstrip("/\\")
        candidates = []
        static_dirs = list(getattr(settings, "STATICFILES_DIRS", []) or [])
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            static_dirs.append(static_root)
        for d in static_dirs:
            candidates.append(Path(d) / rel)
        for c in candidates:
            if c.exists():
                return c.resolve().as_uri()
    except Exception:
        return None
    return None


@dataclass(frozen=True)
class PDFRenderResult:
    bytes: bytes
    filename: str


class PDFGenerator:
    """Service de génération PDF (HTML → PDF)."""

    def __init__(self) -> None:
        try:
            # Import tardif pour éviter de casser l'app si WeasyPrint n'est
            # pas utilisé dans un environnement minimal.
            from weasyprint import HTML  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "WeasyPrint n'est pas disponible. Installez la dépendance via `pip install weasyprint`."
            ) from exc

    def render(self, template_name: str, context: Dict[str, Any], *, base_url: Optional[str] = None) -> bytes:
        """Rend un template Django en PDF via WeasyPrint."""
        from weasyprint import HTML

        html = render_to_string(template_name, context)
        doc = HTML(string=html, base_url=base_url)
        return doc.write_pdf()

    def render_quote(self, quote: "Quote", *, attach: bool = True) -> PDFRenderResult:
        """Génère le PDF de devis (template premium) et peut l'attacher au modèle."""
        from devis.models import Quote  # noqa: F401

        branding = _get_branding()
        logo_url = _resolve_logo_file_url(branding.get("logo_path"))

        ctx = {
            "is_quote": True,
            "quote": quote,
            "items": quote.quote_items.select_related("service").all(),
            "branding": branding,
            "logo_src": logo_url,
        }
        pdf_bytes = self.render("pdf/quote.html", ctx, base_url=str(Path(settings.BASE_DIR).resolve()))

        filename = f"{quote.number or 'devis'}.pdf"
        if attach:
            quote.pdf.save(filename, ContentFile(pdf_bytes), save=False)
            quote.save(update_fields=["pdf"])

        return PDFRenderResult(bytes=pdf_bytes, filename=filename)
