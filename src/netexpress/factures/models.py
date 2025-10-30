"""
Modèles pour la gestion des factures.

Une facture est créée à partir d'un devis une fois que le client accepte
l'offre.  Chaque facture possède un numéro unique, des totaux (HT, TVA, TTC)
et un PDF généré à partir des données de facturation.  La méthode
``generate_pdf`` repose sur ReportLab pour créer un document professionnel.

Depuis 2025, une attention particulière a été portée à la robustesse :
* la génération de PDF lève désormais une erreur explicite si ReportLab n'est
  pas installé, afin d'éviter les plantages silencieux.
* le design de la facture adopte la charte modernisée de NetExpress.

Cette version ne gère pas encore les lignes multiples ni les échéances,
mais constitue une base extensible pour les développements futurs【668280112401708†L16-L63】.
"""

import io
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from typing import List

from django.db import models
from django.core.files.base import ContentFile

from devis.models import Quote, QuoteItem
from .utils import num2words_fr  # utilitaire pour convertir en toutes lettres


class Invoice(models.Model):
    """
    Modèle de facture étendu.

    Une facture est générée à partir d'un devis accepté. Elle contient un numéro
    unique, des dates d'émission et d'échéance, un statut et des champs pour
    enregistrer les totaux HT, TVA et TTC. Les lignes sont stockées dans
    ``InvoiceItem``. Le PDF est généré à partir des données via ReportLab.
    """

    STATUS_CHOICES = [
        ("draft", "Brouillon"),
        ("sent", "Envoyée"),
        ("paid", "Payée"),
        ("partial", "Partiellement payée"),
        ("overdue", "En retard"),
    ]

    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Numéro de facture format NE-AAAA-####, généré automatiquement."
    )
    # Utilise la date actuelle par défaut.  Nous n'employons pas auto_now_add afin
    # d'éviter les migrations interactives si la table existe déjà.
    issue_date = models.DateField(default=date.today)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    # Totaux de la facture
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tva = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    # remise globale en euros
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    # Montant total TTC conservé pour compatibilité.  Ce champ peut être utilisé
    # par des migrations existantes ou des filtres qui attendent une colonne
    # ``amount``.  Il est mis à jour via la méthode ``compute_totals``.
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    pdf = models.FileField(upload_to="factures", blank=True, null=True)

    class Meta:
        ordering = ["-issue_date", "-number"]
        verbose_name = "facture"
        verbose_name_plural = "factures"
        indexes = [models.Index(fields=["number", "issue_date"])]

    def __str__(self) -> str:
        return f"Facture {self.number or ''}"

    @property
    def items(self) -> List["InvoiceItem"]:
        return self.invoice_items.all()

    def save(self, *args, **kwargs):
        # Génération de numéro NE-AAAA-####
        if not self.number:
            year = self.issue_date.year if hasattr(self, "issue_date") and self.issue_date else date.today().year
            prefix = f"NE-{year}-"
            last_inv = Invoice.objects.filter(number__startswith=prefix).order_by("number").last()
            if last_inv:
                try:
                    last_counter = int(last_inv.number.split("-")[-1])
                except ValueError:
                    last_counter = 0
            else:
                last_counter = 0
            self.number = f"{prefix}{last_counter + 1:04d}"
        super().save(*args, **kwargs)

    def compute_totals(self):
        """Calcule les totaux à partir des lignes et applique la remise."""
        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")
        for item in self.items:
            total_ht += item.total_ht
            total_tva += item.total_tva
        total_ht = total_ht - self.discount
        if total_ht < 0:
            total_ht = Decimal("0.00")
        self.total_ht = total_ht.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.tva = total_tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.total_ttc = (self.total_ht + self.tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Mettre à jour le champ ``amount`` pour assurer la compatibilité avec d’anciens schémas
        self.amount = self.total_ttc
        self.save()

    def generate_pdf(self):
        """
        Génère un PDF vectoriel au format A4 reprenant le modèle NetExpress. Le
        PDF contient un en-tête avec bandeau en vagues vertes, les
        coordonnées, le tableau des lignes (zébré) et un récapitulatif
        synthétique avec le montant total en toutes lettres.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise ImportError(
                "ReportLab n'est pas installé. Ajoutez reportlab à vos dépendances pour générer des factures PDF."
            ) from exc

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Couleurs de la charte
        color_primary = colors.HexColor("#0B5D46")
        color_accent = colors.HexColor("#25C17A")

        # Bandeau supérieur en vagues (dessiné avec un chemin).  ReportLab
        # renvoie un objet Path lors de l'appel à beginPath() sur le canvas.
        # Les méthodes moveTo/lineTo/curveTo s'appliquent sur le Path,
        # pas directement sur le Canvas.  Autrefois nous appelions ces
        # méthodes sur le Canvas, ce qui générait une AttributeError.
        c.setFillColor(color_primary)
        bandeau = c.beginPath()
        bandeau.moveTo(0, height)
        bandeau.lineTo(width, height)
        bandeau.lineTo(width, height - 30 * mm)
        bandeau.curveTo(width * 0.75, height - 40 * mm, width * 0.25, height - 20 * mm, 0, height - 30 * mm)
        bandeau.close()
        # Dessiner et remplir le chemin sur le canvas
        c.drawPath(bandeau, fill=1, stroke=0)

        # En-tête texte
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(20 * mm, height - 25 * mm, "NetExpress — Île de Cayenne")
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, height - 31 * mm, "Espaces verts, nettoyage, peinture, bricolage")
        c.drawString(20 * mm, height - 36 * mm, "contact@netexpress.test")

        # Infos facture et client
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(140 * mm, height - 25 * mm, f"Facture {self.number}")
        c.setFont("Helvetica", 9)
        c.drawString(140 * mm, height - 30 * mm, f"Date : {self.issue_date.strftime('%d/%m/%Y')}")
        if self.due_date:
            c.drawString(140 * mm, height - 35 * mm, f"Échéance : {self.due_date.strftime('%d/%m/%Y')}")

        y_offset = height - 60 * mm
        if self.quote:
            client = self.quote.client
        else:
            client = None
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y_offset, "Facturé à :")
        y_offset -= 5 * mm
        c.setFont("Helvetica", 9)
        if client:
            c.drawString(20 * mm, y_offset, client.full_name)
            y_offset -= 4 * mm
            c.drawString(20 * mm, y_offset, client.email)
            y_offset -= 4 * mm
            c.drawString(20 * mm, y_offset, client.phone)
        else:
            c.drawString(20 * mm, y_offset, "Client inconnu")
        y_offset -= 10 * mm

        # Tableau des lignes
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(color_primary)
        c.rect(20 * mm, y_offset, 170 * mm, 6 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.drawString(22 * mm, y_offset + 1.5 * mm, "Description")
        c.drawString(120 * mm, y_offset + 1.5 * mm, "Quantité")
        c.drawString(140 * mm, y_offset + 1.5 * mm, "PU HT")
        c.drawString(160 * mm, y_offset + 1.5 * mm, "Montant HT")
        y_offset -= 6 * mm

        c.setFont("Helvetica", 9)
        zebra = False
        for item in self.items:
            # arrière‑plan zébré
            if zebra:
                c.setFillColor(color_accent)
                c.rect(20 * mm, y_offset, 170 * mm, 6 * mm, fill=1, stroke=0)
            c.setFillColor(colors.black)
            desc = item.description or (item.service.title if item.service else "")
            c.drawString(22 * mm, y_offset + 1.5 * mm, desc[:40])
            c.drawRightString(130 * mm, y_offset + 1.5 * mm, str(item.quantity))
            c.drawRightString(150 * mm, y_offset + 1.5 * mm, f"{item.unit_price:.2f}")
            c.drawRightString(190 * mm, y_offset + 1.5 * mm, f"{item.total_ht:.2f}")
            y_offset -= 6 * mm
            zebra = not zebra

        # Récapitulatif
        y_offset -= 4 * mm
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawRightString(170 * mm, y_offset, "Sous-total HT :")
        c.drawRightString(190 * mm, y_offset, f"{self.total_ht:.2f} €")
        y_offset -= 5 * mm
        c.drawRightString(170 * mm, y_offset, "TVA :")
        c.drawRightString(190 * mm, y_offset, f"{self.tva:.2f} €")
        y_offset -= 5 * mm
        if self.discount > 0:
            c.drawRightString(170 * mm, y_offset, "Remise :")
            c.drawRightString(190 * mm, y_offset, f"- {self.discount:.2f} €")
            y_offset -= 5 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(170 * mm, y_offset, "TOTAL TTC :")
        c.drawRightString(190 * mm, y_offset, f"{self.total_ttc:.2f} €")
        y_offset -= 8 * mm

        # Montant en toutes lettres
        c.setFont("Helvetica", 8)
        c.setFillColor(color_primary)
        amount_words = num2words_fr(self.total_ttc)
        c.drawString(20 * mm, y_offset, f"Montant en toutes lettres : {amount_words} euros")
        y_offset -= 10 * mm

        # Pied de page
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.black)
        c.drawString(20 * mm, 10 * mm, "NetExpress — Île de Cayenne • SIRET 000 000 000 00000 • RIB FR15 1265 9574 0000 0000 0000 123")
        c.drawRightString(200 * mm, 10 * mm, "Merci de votre confiance")

        # Finaliser le PDF
        c.showPage()
        c.save()

        pdf_content = buffer.getvalue()
        buffer.close()
        filename = f"facture_{self.number}.pdf"
        self.pdf.save(filename, ContentFile(pdf_content), save=False)


class InvoiceItem(models.Model):
    """Ligne de facture."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="invoice_items")
    description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("20.00"))

    class Meta:
        verbose_name = "ligne de facture"
        verbose_name_plural = "lignes de facture"

    def __str__(self) -> str:
        return self.description or "Ligne"

    @property
    def total_ht(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_tva(self) -> Decimal:
        return (self.total_ht * self.tax_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_ttc(self) -> Decimal:
        return (self.total_ht + self.total_tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)