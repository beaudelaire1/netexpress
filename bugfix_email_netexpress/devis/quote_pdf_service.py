
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from pathlib import Path

class QuotePdfService:
    @staticmethod
    def generate(quote):
        html = render_to_string("devis/pdf/quote.html", {"quote": quote})
        output_dir = Path(settings.MEDIA_ROOT) / "devis"
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / f"{quote.number}.pdf"
        HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf(pdf_path)
        return pdf_path
