"""Adapter module to integrate the WeasyPrint PDF generator.

This package provides a simple ``WeasyPrintGenerator`` class that wraps
the WeasyPrint library to render Django templates into PDF files.  It
is intentionally named ``weasyprint_adapter`` to avoid conflicting
with the upstream ``weasyprint`` library on the Python import path.
"""

from .pdf_generator import WeasyPrintGenerator  # noqa: F401