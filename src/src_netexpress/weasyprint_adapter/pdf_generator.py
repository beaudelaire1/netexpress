"""
Simple adapter class for generating PDFs using WeasyPrint.

This class wraps the WeasyPrint API and provides a method to render
HTML templates into PDF bytes.  It accepts a Django model instance
(`invoice`) and optional extra context, uses Django’s
``render_to_string`` to build the HTML, and calls WeasyPrint’s
``HTML.write_pdf`` to produce the final document.  The ``base_url``
is set to ``settings.BASE_DIR`` so that static files (like images or
CSS) referenced in the template can be resolved correctly.

Naming this module ``weasyprint_adapter`` avoids clashing with the
third‑party ``weasyprint`` library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.template.loader import render_to_string

try:
    # Import the real WeasyPrint library.  If it's not installed,
    # HTML will be ``None``, and an informative error will be raised
    # when ``generate`` is called.
    from weasyprint import HTML, CSS  # type: ignore
except ImportError:  # pragma: no cover
    HTML = None  # type: ignore
    CSS = None  # type: ignore


class WeasyPrintGenerator:
    """Generate PDF documents from Django templates using WeasyPrint."""

    def __init__(self, template_name: str = "pdf/invoice_premium.html") -> None:
        self.template_name = template_name

    def generate(self, invoice: Any, *, extra_context: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Render the specified template with ``invoice`` and return the PDF bytes.

        Parameters
        ----------
        invoice: Any
            A Django model instance representing the invoice.  The
            template can access its attributes directly (number,
            issue_date, etc.).
        extra_context: Optional[Dict[str, Any]]
            Additional context variables to inject into the template.

        Returns
        -------
        bytes
            The binary content of the rendered PDF.
        """
        if HTML is None:
            raise RuntimeError(
                "WeasyPrint must be installed (and its dependencies) to generate PDFs."
            )
        # Build base context
        context: Dict[str, Any] = {
            "invoice": invoice,
            "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
        }
        if extra_context:
            context.update(extra_context)
        html_string = render_to_string(self.template_name, context)
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        base_url = str(base_dir)
        # Load optional stylesheet using staticfiles finders for production compatibility
        stylesheets = []
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
            candidate = base_dir / "static" / "css" / "pdf.css"
            if candidate.exists():
                css_path = str(candidate)
        
        if css_path and CSS is not None:
            stylesheets.append(CSS(filename=str(css_path)))
        pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf(stylesheets=stylesheets)
        return pdf_bytes