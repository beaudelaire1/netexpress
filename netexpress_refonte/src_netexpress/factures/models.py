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

    def save(self, *args, **kwargs):
        # Generate a number if none is provided.  The format is
        # FAC-YYYY-XXX where YYYY is the year of issue and XXX is a
        # three‑digit sequential counter.  Resetting each year.
        if not self.number:
            year = self.issue_date.year if getattr(self, "issue_date", None) else date.today().year
            prefix = f"FAC-{year}-"
            # Find the last invoice for the current year
            last = Invoice.objects.filter(number__startswith=prefix).order_by("number").last()
            counter = 0
            if last:
                try:
                    counter = int(last.number.split("-")[-1])
                except ValueError:
                    counter = 0
            self.number = f"{prefix}{counter + 1:03d}"
        super().save(*args, **kwargs)

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
        Génère un PDF A4 moderne et, si `attach=True`, l'attache à `self.pdf`.
        - Logo fiable (PNG/JPG/SVG) + cartouche total abaissé
        - Interlignes augmentés
        - En-têtes/colonnes en noir (contraste)
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.graphics.barcode import qr as qrmod
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics import renderPDF
        except ImportError as exc:
            raise ImportError("ReportLab n'est pas installé. `pip install reportlab`") from exc

        branding = _get_branding()

        # Polices (optionnel)
        font_main = "Helvetica"
        font_bold = "Helvetica-Bold"
        if branding.get("font_path"):
            try:
                pdfmetrics.registerFont(TTFont("Brand-Regular", branding["font_path"]))
                font_main = "Brand-Regular"
            except Exception:
                pass
        if branding.get("font_bold_path"):
            try:
                pdfmetrics.registerFont(TTFont("Brand-Bold", branding["font_bold_path"]))
                font_bold = "Brand-Bold"
            except Exception:
                pass

        # Canvas + couleurs
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        c.setTitle(f"Facture {self.number}")
        c.setAuthor(branding["name"])
        c.setSubject("Facture")

        COLOR_PRIMARY = colors.HexColor("#0B5D46")
        COLOR_ACCENT  = colors.HexColor("#F5F7F9")
        COLOR_BORDER  = colors.HexColor("#E5E7EB")
        COLOR_TEXT    = colors.black
        COLOR_MUTED   = colors.HexColor("#6B7280")

        # Marges & interlignes
        M_LEFT, M_RIGHT, M_BOTTOM = 20*mm, 20*mm, 18*mm
        CONTENT_W = width - M_LEFT - M_RIGHT
        LINE_H_TABLE = 5.5*mm
        LINE_H_TEXT  = 5.0*mm

        # Tableau (170 mm total = 210-20-20)
        x0 = M_LEFT
        col_w_desc = 90*mm
        col_w_qty  = 18*mm
        col_w_unit = 24*mm
        col_w_tax  = 18*mm
        col_w_ttc  = 20*mm
        x1 = x0 + col_w_desc
        x2 = x1 + col_w_qty
        x3 = x2 + col_w_unit
        x4 = x3 + col_w_tax
        x5 = x4 + col_w_ttc
        TABLE_W = x5 - x0

        # --- Filigrane de statut
        def _wm():
            """
            Dessine un filigrane "FACTURE" en diagonale.

            Contrairement à la version précédente où le libellé dépendait du statut
            (PAYÉE, BROUILLON, etc.), on utilise ici systématiquement
            "FACTURE" afin d'indiquer clairement la nature du document
            une fois le devis accepté.  La couleur gris clair et la rotation
            assurent que le filigrane reste discret.
            """
            # Choisir un filigrane en fonction du statut de la facture.  Si le
            # statut est « demo » (facture générée à partir d'un devis), on
            # affiche « DEVIS ».  Pour les autres statuts, afficher un
            # libellé spécifique si connu ou « FACTURE » par défaut.
            label_map = {
                "paid": "PAYÉE",
                "draft": "BROUILLON",
                "overdue": "EN RETARD",
                "partial": "PARTIELLE",
                "sent": "ENVOYÉE",
                "demo": "DEVIS",
            }
            label = label_map.get(self.status, "FACTURE")
            c.saveState()
            c.setFillColor(colors.HexColor("#EEEEEE"))
            c.setFont(font_bold, 60)
            c.translate(width / 2, height / 2)
            c.rotate(35)
            c.drawCentredString(0, 0, label)
            c.restoreState()

        # --- Bandeau haut + logo + cartouche Total TTC (ABAISSÉ)
        def _topbar(include_total_card: bool):
            c.setFillColor(COLOR_PRIMARY)
            c.rect(0, height - 6*mm, width, 6*mm, fill=1, stroke=0)

            # Logo fiable
            logo_path = _resolve_logo_path(branding.get("logo_path"))
            logo_ok, logo_w = False, 0
            if logo_path:
                try:
                    if logo_path.lower().endswith(".svg"):
                        from svglib.svglib import svg2rlg
                        drawing = svg2rlg(logo_path)
                        max_h = 30*mm
                        scale = max_h / max(drawing.height or 1, 1)
                        drawing.scale(scale, scale)
                        renderPDF.draw(drawing, c, M_LEFT, height - (max_h + 8*mm))
                        logo_w = drawing.width * scale
                        logo_ok = True
                    else:
                        img = ImageReader(logo_path)
                        iw, ih = img.getSize()
                        max_h = 30*mm
                        w = max_h * (iw / max(ih, 1))
                        c.drawImage(
                            img, M_LEFT, height - (max_h + 8*mm),
                            width=w, height=max_h, mask="auto", preserveAspectRatio=True
                        )
                        logo_w = w
                        logo_ok = True
                except Exception:
                    logo_ok = False

            # Marque + tagline + email
            tx = M_LEFT + (logo_w + 8*mm if logo_ok else 0)
            c.setFillColor(COLOR_TEXT)
            c.setFont(font_bold, 16)
            c.drawString(tx, height - 20*mm, branding["name"])
            c.setFont(font_main, 10)
            c.setFillColor(COLOR_MUTED)
            c.drawString(tx, height - 26*mm, branding["tagline"])
            if branding["email"]:
                c.drawString(tx, height - 26*mm - LINE_H_TEXT, branding["email"])

            # Bloc facture (droite)
            c.setFillColor(COLOR_TEXT)
            c.setFont(font_bold, 12)
            c.drawRightString(width - M_RIGHT, height - 19*mm, f"Facture {self.number}")
            c.setFont(font_main, 9)
            c.drawRightString(width - M_RIGHT, height - 25*mm, f"Date : {self.issue_date.strftime('%d/%m/%Y')}")
            if self.due_date:
                c.drawRightString(width - M_RIGHT, height - 25*mm - LINE_H_TEXT, f"Échéance : {self.due_date.strftime('%d/%m/%Y')}")
            if self.quote:
                qn = getattr(self.quote, "number", None) or getattr(self.quote, "reference", None) or "—"
                c.drawRightString(width - M_RIGHT, height - 25*mm - 2*LINE_H_TEXT, f"Devis : {qn}")

            # Cartouche Total TTC ABBAISSÉ (cy = height - 72*mm)
            if include_total_card:
                c.setFillColor(COLOR_ACCENT)
                cw, ch = 64*mm, 20*mm
                cx, cy = width - M_RIGHT - cw, height - 65*mm  # << abaissé pour ne pas recouvrir le header
                c.roundRect(cx, cy, cw, ch, 3*mm, fill=1, stroke=0)
                c.setFillColor(COLOR_TEXT)
                c.setFont(font_main, 9)
                c.drawString(cx + 4*mm, cy + ch - 7*mm, "Total TTC")
                c.setFont(font_bold, 16)
                c.drawRightString(cx + cw - 4*mm, cy + 7*mm, _money(self.total_ttc))

        # --- Panneaux Émetteur / Client
        def _parties(y: float) -> float:
            ch = 30*mm
            colw = (CONTENT_W - 6*mm) / 2

            # Émetteur
            c.setFillColor(COLOR_ACCENT)
            c.roundRect(M_LEFT, y - ch, colw, ch, 2*mm, fill=1, stroke=0)
            c.setFillColor(COLOR_TEXT)
            # Section title
            c.setFont(font_bold, 12)
            c.drawString(M_LEFT + 4*mm, y - 6*mm, "Émetteur")
            # Branding details
            brand = _get_branding()
            yy = y - 11*mm
            # Nom de l'entreprise (si disponible)
            if brand.get("name"):
                c.setFont(font_bold, 11)
                c.drawString(M_LEFT + 4*mm, yy, brand["name"])
                yy -= LINE_H_TEXT
                c.setFont(font_main, 11)
            # Adresse (chaque ligne)
            for line in brand.get("address_lines", []):
                c.drawString(M_LEFT + 4*mm, yy, line)
                yy -= LINE_H_TEXT
            # Coordonnées de contact
            # Afficher d'abord les numéros de téléphone afin de mettre en avant
            # le contact direct (fixe et mobile).  L'adresse e‑mail est
            # affichée en dernier si nécessaire.
            if brand.get("phone"):
                c.drawString(M_LEFT + 4*mm, yy, brand["phone"])
                yy -= LINE_H_TEXT
            # Ne pas afficher l'e‑mail par défaut, sauf si aucune autre
            # coordonnée n'est fournie.
            if brand.get("email") and not brand.get("phone"):
                c.drawString(M_LEFT + 4*mm, yy, brand["email"])
                yy -= LINE_H_TEXT
            if brand.get("website"):
                c.drawString(M_LEFT + 4*mm, yy, brand["website"])
                yy -= LINE_H_TEXT
            # Mentions légales et fiscales (TVA intracommunautaire uniquement).  Le numéro SIRET
            # n'est plus affiché dans l'émetteur pour simplifier la présentation.
            c.setFillColor(COLOR_MUTED)
            # Ne pas afficher le SIRET (réservé aux mentions légales).  Conserver uniquement la TVA.
            if brand.get("tva_intra"):
                c.drawString(M_LEFT + 4*mm, yy, f"TVA {brand['tva_intra']}")

            # Client
            cx = M_LEFT + colw + 6*mm
            c.setFillColor(COLOR_ACCENT)
            c.roundRect(cx, y - ch, colw, ch, 2*mm, fill=1, stroke=0)
            c.setFillColor(COLOR_TEXT)
            c.setFont(font_bold, 12)
            c.drawString(cx + 4*mm, y - 6*mm, "Client")
            c.setFont(font_main, 11)
            yy = y - 11*mm
            cli = self.quote.client if self.quote else None
            if cli:
                c.drawString(cx + 4*mm, yy, _safe_get(cli, "full_name", "Client")); yy -= LINE_H_TEXT
                em = _safe_get(cli, "email", ""); ph = _safe_get(cli, "phone", "")
                if em:
                    c.drawString(cx + 4*mm, yy, em); yy -= LINE_H_TEXT
                if ph:
                    c.drawString(cx + 4*mm, yy, ph); yy -= LINE_H_TEXT
                addr = ", ".join(s for s in [
                    _safe_get(cli, "address_line1", ""), _safe_get(cli, "address_line2", ""),
                    _safe_get(cli, "postal_code", ""), _safe_get(cli, "city", "")
                ] if s)
                if addr:
                    c.drawString(cx + 4*mm, yy, addr)
            else:
                c.drawString(cx + 4*mm, yy, "Client inconnu")

            return y - ch - 10*mm

        # --- En-tête tableau
        def _thead(y: float) -> float:
            c.setFillColor(colors.HexColor("#F3F4F6"))
            c.rect(x0, y - 8*mm, TABLE_W, 8*mm, fill=1, stroke=0)
            c.setFillColor(COLOR_TEXT)
            c.setFont(font_bold, 11)
            c.drawString(x0 + 2*mm, y - 5.5*mm, "Description")
            c.drawRightString(x2 - 2*mm, y - 5.5*mm, "Quantité")
            c.drawRightString(x3 - 2*mm, y - 5.5*mm, "PU HT")
            c.drawRightString(x4 - 2*mm, y - 5.5*mm, "TVA %")
            c.drawRightString(x5 - 2*mm, y - 5.5*mm, "Montant TTC")
            c.setStrokeColor(COLOR_BORDER)
            c.setLineWidth(0.3)
            c.line(x0, y - 8*mm, x5, y - 8*mm)
            return y - 8*mm

        # --- Footer (par page)
        def _footer():
            c.setFont(font_main, 7)
            c.setFillColor(COLOR_MUTED)
            left = branding["name"]
            # Supprimer l'affichage du numéro SIRET dans le pied de page.  Seule la TVA
            # intracommunautaire est ajoutée aux mentions légales.
            if branding.get("tva_intra"):
                left += f" • TVA {branding['tva_intra']}"
            c.drawString(M_LEFT, M_BOTTOM - 2*mm, left)
            right = []
            if branding.get("iban"):
                right.append(f"IBAN {branding['iban']}")
            if branding.get("bic"):
                right.append(f"BIC {branding['bic']}")
            right.append(f"Page {c.getPageNumber()}")
            c.drawRightString(width - M_RIGHT, M_BOTTOM - 2*mm, " • ".join(right))

        # --- Saut de page
        def _maybe_new(y: float, need: float, repeat_header=True) -> float:
            if y - need < M_BOTTOM + 34*mm:
                _footer()
                c.showPage()
                _wm()
                _topbar(include_total_card=False)
                y2 = height - 60*mm
                if repeat_header:
                    y2 = _thead(y2)
                return y2
            return y

        # --- Corps du tableau
        def _tbody(y: float) -> float:
            from reportlab.pdfbase import pdfmetrics as _pm
            c.setFont(font_main, 9)
            zebra = False

            for it in self.items:
                desc = (it.description or "").strip()
                lines = _wrap_text(desc, (x1 - x0) - 4*mm, _pm, font_main, 9)
                row_h = max(LINE_H_TABLE * max(1, len(lines)), 7*mm)
                y = _maybe_new(y, row_h, True)

                if zebra:
                    c.setFillColor(COLOR_ACCENT)
                    c.rect(x0, y - row_h, TABLE_W, row_h, fill=1, stroke=0)

                c.setFillColor(COLOR_TEXT)
                base_y = y - 3.6*mm
                cy = base_y
                for ln in lines:
                    c.drawString(x0 + 2*mm, cy, ln)
                    cy -= LINE_H_TABLE

                c.drawRightString(x2 - 2*mm, base_y, str(it.quantity))
                c.drawRightString(x3 - 2*mm, base_y, f"{it.unit_price:.2f}")
                c.drawRightString(x4 - 2*mm, base_y, f"{it.tax_rate:.2f}")
                c.drawRightString(x5 - 2*mm, base_y, f"{it.total_ttc:.2f}")

                # Dessiner la ligne de séparation horizontale en couleur neutre
                c.setStrokeColor(COLOR_BORDER)
                c.setLineWidth(0.25)
                c.line(x0, y - row_h, x5, y - row_h)
                # Colonnes : utiliser des couleurs contrastées pour mieux
                # distinguer les séparateurs.  Les bords extérieurs sont en noir
                # (COLOR_TEXT) tandis que les séparations internes sont en vert
                # primaire (COLOR_PRIMARY).  On ajuste également l'épaisseur.
                for xv in (x0, x1, x2, x3, x4, x5):
                    if xv in (x0, x5):
                        c.setStrokeColor(COLOR_TEXT)
                    else:
                        c.setStrokeColor(COLOR_PRIMARY)
                    c.setLineWidth(0.3)
                    c.line(xv, y, xv, y - row_h)

                y -= row_h
                zebra = not zebra
            return y

        # --- Récap + décomposition TVA + QR + montant en lettres
        def _vat_and_summary(y: float) -> float:
            """
            Dessine le tableau récapitulatif des montants et la décomposition de la
            TVA.

            Afin d'améliorer la lisibilité des remises, ce bloc affiche
            systématiquement le montant hors taxe initial (avant remise), la
            remise appliquée, puis le montant hors taxe net.  La TVA et le total
            TTC sont calculés sur la base du montant net.  En l'absence de
            remise, le champ « Sous‑total HT » est directement le net HT.
            """
            # Préparer la décomposition de la TVA pour chaque taux
            vat_map: Dict[Decimal, Dict[str, Decimal]] = {}
            total_ht_pre_discount = Decimal("0.00")
            for it in self.items:
                r = it.tax_rate
                vat_map.setdefault(r, {"base": Decimal("0.00"), "vat": Decimal("0.00")})
                vat_map[r]["base"] += it.total_ht
                vat_map[r]["vat"]  += it.total_tva
                total_ht_pre_discount += it.total_ht

            y = _maybe_new(y, 42*mm, False)

            rl, rv = x4 - 8*mm, x5 - 2*mm
            c.setFillColor(COLOR_TEXT)
            c.setFont(font_bold, 9)
            # Afficher le sous‑total avant remise s'il y a une remise
            if self.discount and total_ht_pre_discount > 0:
                c.drawRightString(rl, y, "Sous-total HT :")
                c.drawRightString(rv, y, _money(total_ht_pre_discount))
                y -= LINE_H_TEXT
                # Remise appliquée
                c.setFont(font_main, 9)
                c.drawRightString(rl, y, "Remise :")
                c.drawRightString(rv, y, f"- {_money(self.discount)}")
                y -= LINE_H_TEXT
                # Montant net après remise
                c.setFont(font_main, 9)
                c.drawRightString(rl, y, "Net HT :")
                c.drawRightString(rv, y, _money(self.total_ht))
                y -= LINE_H_TEXT
            else:
                # Sans remise, on affiche simplement le sous‑total HT
                c.drawRightString(rl, y, "Sous-total HT :")
                c.drawRightString(rv, y, _money(self.total_ht))
                y -= LINE_H_TEXT

            # TVA globale après remise (si applicable)
            c.setFont(font_main, 9)
            c.drawRightString(rl, y, "TVA :")
            c.drawRightString(rv, y, _money(self.tva))
            y -= LINE_H_TEXT

            # Détail par taux
            for rate, comp in sorted(vat_map.items(), key=lambda x: x[0], reverse=True):
                c.setFillColor(COLOR_MUTED)
                c.setFont(font_main, 8)
                c.drawRightString(rl, y, f"• TVA {rate:.2f}% sur {_money(comp['base'])} :")
                c.drawRightString(rv, y, _money(comp["vat"]))
                y -= (LINE_H_TEXT - 0.8*mm)

            # Total TTC net après remise
            c.setFillColor(COLOR_TEXT)
            c.setFont(font_bold, 10)
            c.drawRightString(rl, y, "TOTAL TTC :")
            c.drawRightString(rv, y, _money(self.total_ttc))
            y -= (LINE_H_TEXT + 2*mm)

            # QR (optionnel)
            tmpl = branding.get("payment_qr_data_template", "")
            if tmpl:
                try:
                    payload = tmpl.format(
                        number=self.number, total=str(self.total_ttc),
                        iban=branding.get("iban", ""), bic=branding.get("bic", "")
                    )
                    w = 26*mm
                    widget = qrmod.QrCodeWidget(payload)
                    b = widget.getBounds()
                    ww, hh = b[2] - b[0], b[3] - b[1]
                    d = Drawing(w, w, transform=[w / ww, 0, 0, w / hh, 0, 0])
                    d.add(widget)
                    renderPDF.draw(d, c, x0, y - w + 2*mm)
                    c.setFillColor(COLOR_MUTED)
                    c.setFont(font_main, 7)
                    c.drawString(x0 + w + 3*mm, y - 6*mm, "Scanner pour payer")
                except Exception:
                    pass

            # Montant en toutes lettres
            c.setFillColor(COLOR_PRIMARY)
            c.setFont(font_main, 8)
            try:
                words = _num2words_fr(self.total_ttc)
                c.drawString(x0, y - 8*mm, f"Montant en toutes lettres : {words} euros")
                y -= (LINE_H_TEXT + 6*mm)
            except Exception:
                y -= 4*mm

            return y

        # --- Notes / Conditions (si présentes)
        def _notes_terms(y: float) -> float:
            notes = (self.notes or "").strip() or branding.get("default_notes", "")
            terms = (self.payment_terms or "").strip() or branding.get("payment_terms", "")
            from reportlab.pdfbase import pdfmetrics as _pm
            for title, text in (("Notes", notes), ("Conditions de paiement", terms)):
                if not text:
                    continue
                y = _maybe_new(y, 18*mm, False)
                c.setFillColor(COLOR_ACCENT)
                c.roundRect(M_LEFT, y - 18*mm, CONTENT_W, 18*mm, 2*mm, fill=1, stroke=0)
                c.setFillColor(COLOR_TEXT)
                c.setFont(font_bold, 9)
                c.drawString(M_LEFT + 4*mm, y - 6*mm, title)
                c.setFont(font_main, 8)
                c.setFillColor(COLOR_TEXT)
                max_w = CONTENT_W - 8*mm
                line, yy = "", y - 11*mm
                for w in text.split():
                    test = (line + " " + w).strip()
                    if _pm.stringWidth(test, font_main, 8) <= max_w:
                        line = test
                    else:
                        c.drawString(M_LEFT + 4*mm, yy, line)
                        yy -= (LINE_H_TEXT - 1*mm)
                        line = w
                if line:
                    c.drawString(M_LEFT + 4*mm, yy, line)
                    yy -= (LINE_H_TEXT - 1*mm)
                y = yy - 4*mm
            return y

        # --- Signature et mention "Bon pour accord"
        def _signature_block(y: float) -> float:
            """
            Dessine un encart réservé à la signature en bas de page.

            Cette zone comporte un cadre vide où le client peut signer
            et un petit texte d'accompagnement invitant à ajouter la
            mention manuscrite « Bon pour accord ».  L'espace requis
            est d'environ 25 mm de hauteur.

            Parameters
            ----------
            y : float
                Position verticale actuelle du curseur (en points).

            Returns
            -------
            float
                Nouvelle position verticale après avoir dessiné
                l'encart.
            """
            from reportlab.lib.units import mm
            height_needed = 25 * mm
            # S'assurer qu'il reste suffisamment d'espace; ne pas répéter
            y = _maybe_new(y, height_needed, False)
            box_w, box_h = 60 * mm, 20 * mm
            x_sig = M_LEFT
            # Cadre pour signature
            c.setStrokeColor(COLOR_BORDER)
            c.setLineWidth(0.5)
            c.rect(x_sig, y - box_h, box_w, box_h, fill=0, stroke=1)
            # Texte d'invitation
            c.setFont(font_main, 7)
            c.setFillColor(COLOR_MUTED)
            msg = "Veuillez ajouter la mention ‘Bon pour accord’ et signer ci‑dessus."
            c.drawString(x_sig, y - box_h - 3 * mm, msg)
            # Retourner la nouvelle position
            return y - box_h - 6 * mm

        # --- Rendu
        _wm()
        _topbar(include_total_card=True)
        y = height - 68*mm
        y = _parties(y)
        y = _thead(y)
        y = _tbody(y)
        y = _vat_and_summary(y)
        y = _notes_terms(y)
        # Ne pas ajouter de bloc de signature (Bon pour accord) sur la facture
        _footer()
        c.save()  # pas de showPage final (évite page blanche)

        pdf = buf.getvalue()
        buf.close()
        if attach:
            # Nom de fichier basé sur le numéro de facture.  En utilisant
            # exclusivement ce nom (sans réappliquer le répertoire ``upload_to``),
            # on évite la création de sous‑dossiers « factures/factures/… » lors des
            # générations successives.
            filename = f"{self.number}.pdf"
            # Supprimer l'ancien fichier attaché pour éviter les doublons.
            if self.pdf:
                try:
                    self.pdf.delete(save=False)
                except Exception:
                    pass
            # Enregistrez le fichier PDF avec le nom simple.  Django le placera
            # automatiquement dans le répertoire ``upload_to`` configuré pour le champ.
            self.pdf.save(filename, ContentFile(pdf), save=False)
        return pdf


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
