"""
Models for invoice management.

An invoice is created from a quote once the customer accepts the offer.  Each
invoice stores a reference to the originating quote, a unique number, the
invoice amount and a generated PDF file.  The ``generate_pdf`` method can
create a simple invoice document using the ReportLab library.
"""

import io
from decimal import Decimal
from datetime import datetime

from django.db import models
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

from quotes.models import Quote


class Invoice(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    pdf = models.FileField(upload_to="invoices", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "facture"
        verbose_name_plural = "factures"

    def __str__(self) -> str:
        return f"Facture {self.number} pour {self.quote.name}"

    def generate_number(self) -> str:
        """Generate a simple invoice number based on the date and ID."""
        date_part = self.created_at.strftime("%Y%m%d") if self.created_at else datetime.now().strftime("%Y%m%d")
        return f"INV{date_part}{self.pk or ''}"

    def generate_pdf(self):
        """
        Create a PDF representation of the invoice using ReportLab.

        This method writes a simple invoice layout into an in-memory buffer
        and assigns it to the ``pdf`` field.  It assumes that ReportLab is
        installed and available.  The PDF includes the company name, client
        information, invoice number, date, and a summary of the service and
        amount due.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20 * mm, height - 30 * mm, "NetExpress")
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, height - 40 * mm, "Entreprise de nettoyage et entretien")
        c.drawString(20 * mm, height - 45 * mm, "contact@netexpress.test")

        # Client info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, height - 60 * mm, "Facturé à :")
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, height - 65 * mm, self.quote.name)
        c.drawString(20 * mm, height - 70 * mm, self.quote.email)
        c.drawString(20 * mm, height - 75 * mm, self.quote.phone)

        # Invoice details
        c.setFont("Helvetica-Bold", 14)
        c.drawString(120 * mm, height - 30 * mm, f"Facture {self.number}")
        c.setFont("Helvetica", 10)
        invoice_date = self.created_at.strftime("%d/%m/%Y") if self.created_at else datetime.now().strftime("%d/%m/%Y")
        c.drawString(120 * mm, height - 35 * mm, f"Date : {invoice_date}")

        # Service summary
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, height - 90 * mm, "Description")
        c.drawString(150 * mm, height - 90 * mm, "Montant (€)")
        c.setFont("Helvetica", 10)
        y = height - 100 * mm
        service_description = self.quote.service or "Service sur mesure"
        c.drawString(20 * mm, y, service_description)
        c.drawString(150 * mm, y, f"{self.amount:.2f}")

        # Total
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y - 15 * mm, "Total")
        c.drawString(150 * mm, y - 15 * mm, f"{self.amount:.2f}")

        c.showPage()
        c.save()

        pdf_content = buffer.getvalue()
        buffer.close()
        filename = f"invoice_{self.number}.pdf"
        self.pdf.save(filename, ContentFile(pdf_content), save=False)