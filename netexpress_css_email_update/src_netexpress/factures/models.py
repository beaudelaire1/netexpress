"""
factures/models.py — Version complète & professionnelle

✔ Logo PNG/JPG/SVG (chemin absolu, "static:...", ou relatif media/static) — rendu fiable
✔ Cartouche "Total TTC" abaissé pour ne pas chevaucher le header (cy = height - 72*mm)
✔ Interlignes augmentés (aucun texte tronqué)
✔ Panneaux Émetteur / Client
✔ Tableau 5 colonnes (Description | Quantité | PU HT | TVA % | Montant TTC)
✔ Pagination avec en-tête répété
✔ Récapitulatif + décomposition TVA par taux
✔ QR de paiement (optionnel)
✔ Filigrane de statut, numéros de page, métadonnées PDF
✔ FK en chaîne vers "devis.Quote" (pas d’import circulaire)
✔ Fallback si .utils.num2words_fr indisponible

Dépendances : reportlab (obligatoire), svglib (si logo SVG).
"""
import io
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Dict, Optional

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile


# =========================
# Helpers (robustes)
# =========================

def _num2words_fr(v: Decimal) -> str:
    """Import tardif de .utils.num2words_fr, repli numérique FR si absent."""
    try:
        from .utils import num2words_fr as _n2w
        return _n2w(v)
    except Exception:
        return str(v).replace(".", ",")

def _money(value: Decimal) -> str:
    return f"{value:.2f} €".replace(".", ",")

def _safe_get(obj, attr, default=""):
    try:
        val = getattr(obj, attr)
        return val if val is not None else default
    except Exception:
        return default

def _wrap_text(text: str, max_width: float, pdfmetrics, font_name: str, font_size: int) -> List[str]:
    words = (text or "").split()
    if not words:
        return [""]
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def _resolve_logo_path(path: Optional[str]) -> Optional[str]:
    """
    Résout le logo depuis :
      - chemin absolu existant
      - staticfiles : "static:img/logo.svg" ou "img/logo.svg"
      - MEDIA_ROOT / <path> (fallback)
    """
    if not path:
        return None
    if os.path.isabs(path) and os.path.exists(path):
        return path
    # staticfiles
    try:
        from django.contrib.staticfiles import finders
        rel = path.replace("static:", "").lstrip("/\\")
        sp = finders.find(rel)
        if sp and os.path.exists(sp):
            return sp
    except Exception:
        pass
    # media fallback
    mr = getattr(settings, "MEDIA_ROOT", None)
    if mr:
        mp = os.path.join(mr, path.lstrip("/\\"))
        if os.path.exists(mp):
            return mp
    return None

def _get_branding() -> dict:
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
        "tagline": cfg.get("tagline", "Espaces verts, nettoyage, peinture, bricolage"),
        "email": cfg.get("email", "contact@exemple.fr"),
        "phone": cfg.get("phone", ""),
        "website": cfg.get("website", ""),
        "address_lines": addr_lines,
        "siret": cfg.get("siret", ""),
        "tva_intra": cfg.get("tva_intra", ""),
        "iban": cfg.get("iban", ""),
        "bic": cfg.get("bic", ""),
        "logo_path": cfg.get("logo_path", None),          # "static:img/logo.svg" ou chemin absolu
        "font_path": cfg.get("font_path", None),          # .ttf optionnel
        "font_bold_path": cfg.get("font_bold_path", None),
        "payment_qr_data_template": cfg.get("payment_qr_data_template", ""),
        "default_notes": cfg.get("default_notes", ""),
        "payment_terms": cfg.get("payment_terms", ""),
    }


# =========================
# Modèles
# =========================

class Invoice(models.Model):

    class InvoiceStatus(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        REFACTURATION = "refacturation", _("Refacturation")
        AVOIR = "avoir", _("Avoir")
        DEMO = "demo", _("Devis")
        SENT = "sent", _("Envoyée")
        PAID = "paid", _("Payée")
        PARTIAL = "partial", _("Partiellement payée")
        OVERDUE = "overdue", _("En retard")

    # Référence en chaîne => évite tout import circulaire
    quote = models.ForeignKey("devis.Quote", on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")

    number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Numéro FAC-AAAA-XXX, généré automatiquement si vide."
    )
    issue_date = models.DateField(default=date.today)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField( max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    # Totaux
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tva = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Compat historique
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Contenu & sortie
    notes = models.TextField(blank=True, default="")
    payment_terms = models.TextField(blank=True, default="")
    pdf = models.FileField(upload_to="factures", blank=True, null=True)

    class Meta:
        ordering = ["-issue_date", "-number"]
        indexes = [models.Index(fields=["number", "issue_date"])]
        verbose_name = _("facture")
        verbose_name_plural = _("factures")

    def __str__(self) -> str:
        return f"Facture {self.number or '—'}"

    @property
    def items(self) -> List["InvoiceItem"]:
        return list(self.invoice_items.all())

    def save(self, *args, **kwargs) -> None:
        """
        Override the default save to assign a unique invoice number when none
        is provided.  The numbering scheme follows the pattern
        ``FAC-YYYY-XXX`` where ``YYYY`` is the year of the issue date and
        ``XXX`` is a zero‑padded incremental counter.  To avoid race
        conditions when multiple invoices are created concurrently, the
        calculation of the next counter value is wrapped inside a database
        transaction and uses ``select_for_update()`` to lock the last
        invoice row for the given year.  When editing an existing invoice
        (i.e. ``self.pk`` is set), the number is left untouched.

        Parameters
        ----------
        *args, **kwargs
            Forwarded to the parent ``save`` implementation.
        """
        # Only generate a number for new invoices when none is provided
        if not self.pk and not self.number:
            # Determine the year either from the issue_date field or today
            year = self.issue_date.year if getattr(self, "issue_date", None) else date.today().year
            prefix = f"FAC-{year}-"
            from django.db import transaction
            # Use an atomic block to avoid race conditions.  Lock the last
            # invoice row for the given year so that concurrent creates don't
            # read the same counter value.
            with transaction.atomic():
                last = (
                    Invoice.objects
                    .select_for_update()
                    .filter(number__startswith=prefix)
                    .order_by("number")
                    .last()
                )
                counter = 0
                if last:
                    try:
                        counter = int(str(last.number).split("-")[-1])
                    except Exception:
                        # If parsing fails, reset the counter
                        counter = 0
                # Compose the new number
                self.number = f"{prefix}{counter + 1:03d}"
        super().save(*args, **kwargs)

    @classmethod
    def create_from_quote(cls, quote: "devis.Quote") -> "Invoice":
        """
        Create a new invoice from a given quote.  This helper copies all
        line items from the quote into the invoice and computes the totals.
        The operation is wrapped in a transaction to ensure that either
        everything is created successfully or nothing is persisted.

        Parameters
        ----------
        quote : devis.Quote
            The quote instance from which to generate the invoice.

        Returns
        -------
        Invoice
            The newly created invoice populated with items from the quote.
        """
        from django.db import transaction
        # Late import to avoid a circular dependency when loading models
        from .models import InvoiceItem  # type: ignore
        with transaction.atomic():
            # Instantiate the invoice linked to the quote
            invoice = cls.objects.create(quote=quote, issue_date=date.today())
            # Copy each quote item into an invoice item.  Use getattr to
            # gracefully handle quotes without items (e.g. if relation is empty).
            try:
                quote_items = quote.items.all()  # type: ignore[attr-defined]
            except Exception:
                quote_items = []
            for item in quote_items:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=getattr(item, "description", ""),
                    quantity=getattr(item, "quantity", 1),
                    unit_price=getattr(item, "unit_price", Decimal("0.00")),
                    tax_rate=getattr(item, "tax_rate", Decimal("0.00")),
                )
            # Compute the totals after all items have been added
            invoice.compute_totals()
        return invoice

    def compute_totals(self):
        """
        Calcule les totaux HT, TVA et TTC en tenant compte de la remise.

        La remise est appliquée sur le montant hors taxe.  Pour éviter
        une incohérence entre la remise et la TVA, la TVA est réduite
        proportionnellement à la part de remise.  Exemple : si la
        remise représente 10 % du HT, la TVA totale est également
        réduite de 10 %.  Le montant TTC est ensuite recomposé à
        partir du HT remisé et de la TVA ajustée.
        """
        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")
        for it in self.items:
            total_ht += it.total_ht
            total_tva += it.total_tva
        # Calculer la remise effective et l'appliquer proportionnellement
        discount = self.discount or Decimal("0.00")
        if discount > 0 and total_ht > 0:
            # Ratio de remise sur le HT original
            ratio = (discount / total_ht).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            # Appliquer la remise
            total_ht -= discount
            total_tva -= (total_tva * ratio)
        # Empêcher les montants négatifs
        if total_ht < 0:
            total_ht = Decimal("0.00")
        if total_tva < 0:
            total_tva = Decimal("0.00")
        self.total_ht = total_ht.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.tva = total_tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.total_ttc = (self.total_ht + self.tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.amount = self.total_ttc
        self.save(update_fields=["total_ht", "tva", "total_ttc", "amount"])

    # =========================
    # Génération PDF (pro)
    # =========================
    def generate_pdf(self, attach: bool = True) -> bytes:
        """
        Délègue la génération du PDF à un service externe.

        Cette méthode crée une instance de ``PDFInvoiceGenerator``
        (définie dans ``factures.services.pdf_generator``) et appelle sa
        méthode ``generate_pdf``.  Toutes les options et la logique
        d'assemblage du document sont ainsi centralisées en dehors
        du modèle, ce qui simplifie la maintenance et respecte le
        principe de responsabilité unique.

        Parameters
        ----------
        attach : bool
            Si ``True``, le PDF est enregistré dans le champ ``pdf`` de
            l'instance.  Sinon, seuls les octets sont retournés.

        Returns
        -------
        bytes
            Le contenu du fichier PDF généré.
        """
        from .services.pdf_generator import PDFInvoiceGenerator
        generator = PDFInvoiceGenerator(self)
        return generator.generate_pdf(attach=attach)


class InvoiceItem(models.Model):
    """Ligne de facture."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="invoice_items")
    description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = _("ligne de facture")
        verbose_name_plural = _("lignes de facture")

    def __str__(self) -> str:
        return self.description or "Ligne"

    @property
    def total_ht(self) -> Decimal:
        return (self.unit_price * Decimal(self.quantity)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_tva(self) -> Decimal:
        return (self.total_ht * self.tax_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_ttc(self) -> Decimal:
        return (self.total_ht + self.total_tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
