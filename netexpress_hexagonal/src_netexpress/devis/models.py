"""
Modèles pour la gestion des devis.

L'application ``devis`` gère les entités suivantes :

* ``Client`` : représente un contact (particulier ou entreprise) qui demande un devis.
  Les champs incluent nom complet, email, téléphone et adresse.  Cette entité
  peut être enrichie selon les besoins (ex. société, SIREN).

* ``Quote`` : une demande de devis associée à un client.  Elle contient un
  numéro unique, un statut et des champs pour le service souhaité, un message
  libre et des totaux (HT, TVA, TTC) pour préparer la conversion en
  facture.  Les totaux peuvent être calculés via la méthode ``compute_totals``.

* ``QuoteItem`` : une ligne de devis liée à un service ou à une description
  libre, avec quantité, prix unitaire et taux de TVA.

Depuis 2025, les formulaires associés exigent un numéro de téléphone et la
présentation a été améliorée avec des visuels locaux (stockés dans
``static/img``).  Les modèles restent compatibles avec l'interface
d'administration et les actions de génération de factures.  Les
dépendances à Unsplash ont été supprimées pour garantir un rendu fiable.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from django.db import models
from django.utils.text import slugify
from services.models import Service
from typing import List


class Client(models.Model):
    """Informations de contact pour une demande de devis."""
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "client"
        verbose_name_plural = "clients"

    def __str__(self) -> str:
        return self.full_name


class Quote(models.Model):
    """Demande de devis.

    Un numéro de devis est généré automatiquement à partir de l'année et de
    l'identifiant.  Le champ ``service`` est optionnel pour permettre des
    demandes libres.  Le statut permet de suivre l'avancement (brouillon,
    envoyé, accepté, rejeté).  Les totaux permettent d'anticiper la facture.
    """

    STATUS_CHOICES = [
        ("draft", "Brouillon"),
        ("sent", "Envoyé"),
        ("accepted", "Accepté"),
        ("rejected", "Rejeté"),
    ]

    number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Numéro de devis format DEV-AAAA-XXX, généré automatiquement."
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="quotes")
    # Lorsque plusieurs services sont ajoutés via les items, ce champ reste optionnel
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
        help_text="Service principal demandé (optionnel si plusieurs items)."
    )
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    # Date d'émission du devis.  Utilise la date du jour par défaut afin d'éviter les
    # problèmes de migration avec auto_now_add.  La valeur est fixée lors de la création
    # et peut être modifiée par l'administrateur si nécessaire.
    issue_date = models.DateField(default=date.today)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Totaux calculés pour le devis.  Ces champs sont renseignés via compute_totals().
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tva = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # PDF file attached to the quote.  When a quote is generated the
    # associated PDF is stored here.  The file is saved under
    # ``media/devis/`` and named after the quote number.  This field
    # allows automated emailing of professional quotes and a central
    # repository of generated documents.
    pdf = models.FileField(upload_to="devis", blank=True, null=True)

    def __str__(self) -> str:
        return f"Devis {self.number or ''} pour {self.client.full_name}"

    def save(self, *args, **kwargs):
        # Attribution d'un numéro de devis si nécessaire : DEV-AAAA-XXX
        if not self.number:
            # l'année est celle de la date d'émission
            year = self.issue_date.year if getattr(self, "issue_date", None) else date.today().year
            prefix = f"DEV-{year}-"
            last_number = Quote.objects.filter(number__startswith=prefix).order_by("number").last()
            if last_number:
                try:
                    last_counter = int(last_number.number.split("-")[-1])
                except ValueError:
                    last_counter = 0
            else:
                last_counter = 0
            # Use a three‑digit counter (000–999)
            self.number = f"{prefix}{last_counter + 1:03d}"
        # Définir une date de validité par défaut (30 jours) si non
        # renseignée.  Cette logique est placée dans ``save`` afin
        # d'éviter des migrations supplémentaires et de garantir un
        # comportement homogène lors de la création via l'admin ou l'API.
        if not self.valid_until and getattr(self, "issue_date", None):
            from datetime import timedelta
            self.valid_until = self.issue_date + timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def items(self) -> List["QuoteItem"]:
        return self.quote_items.all()

    def compute_totals(self):
        """Calcule et met à jour les totaux HT, TVA et TTC à partir des items.

        Cette implémentation délègue la logique de calcul à la couche
        hexagonale (application service) afin de séparer la logique
        métier du modèle Django.  La méthode utilise un repository
        d'adaptateur pour convertir l'instance en entité de domaine,
        calculer les totaux et les réinjecter dans la base de données.
        """
        try:
            # Lazy import pour éviter les dépendances circulaires
            from hexagon.infrastructure.repositories import QuoteRepository
            from hexagon.application.services import QuoteService
            repo = QuoteRepository()
            service = QuoteService(repo)
            service.compute_totals(self.pk)
            # Rafraîchir les valeurs depuis la base de données pour refléter les modifications
            self.refresh_from_db(fields=["total_ht", "tva", "total_ttc"])
        except Exception:
            # Si le service n'est pas disponible (par ex. tests sans Django),
            # revenir à l'implémentation locale pour garantir la compatibilité.
            total_ht = Decimal("0.00")
            total_tva = Decimal("0.00")
            for item in self.items:
                total_ht += item.total_ht
                total_tva += item.total_tva
            self.total_ht = total_ht.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.tva = total_tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.total_ttc = (self.total_ht + self.tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.save(update_fields=["total_ht", "tva", "total_ttc"])

    # ------------------------------------------------------------------
    # PDF generation
    # ------------------------------------------------------------------
    def generate_pdf(self, attach: bool = True) -> bytes:
        """
        Génère un document PDF décrivant ce devis.

        Le PDF inclut l'en‑tête de la société, les coordonnées du client,
        la liste des lignes de devis et un tableau récapitulatif des
        montants HT, TVA et TTC.  Un encart « Bon pour accord » et une
        zone de signature sont également ajoutés.  Si ``attach`` est
        ``True``, le PDF est enregistré dans le champ ``pdf`` de
        l'instance et une nouvelle version est générée à chaque appel.

        :param attach: si vrai, le fichier est rattaché au modèle
        :return: le contenu binaire du PDF généré
        :raises ImportError: si ReportLab n'est pas installé
        """
        # ReportLab importé à la demande pour éviter des dépendances
        # obligatoires si la génération n'est pas utilisée.
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
        except ImportError as exc:
            raise ImportError(
                "La génération de PDF pour les devis requiert ReportLab. "
                "Installez la dépendance via pip (reportlab>=4.0)."
            ) from exc
        from django.conf import settings
        from django.core.files.base import ContentFile
        # Le modèle QuoteItem est importé localement uniquement pour
        # éviter des importations circulaires dans d'autres modules.  Il
        # n'est pas utilisé directement ici mais conservé pour référence.
        from .models import QuoteItem  # noqa: F401

        # Préparer le tampon PDF
        import io
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # ------------------------------------------------------------------
        # Filigrane DEVIS
        # ------------------------------------------------------------------
        # Avant tout dessin, ajouter un filigrane léger « DEVIS » centré et
        # incliné.  L'opacité est simulée via une couleur gris clair.
        c.saveState()
        c.setFillColor(colors.HexColor("#F0F0F0"))
        c.setFont("Helvetica-Bold", 60)
        c.translate(width / 2, height / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "DEVIS")
        c.restoreState()
        # Marges
        left_margin = 20 * mm
        right_margin = 20 * mm
        top_margin = 30 * mm
        bottom_margin = 20 * mm
        y = height - top_margin

        # Informations de branding depuis les factures pour réutiliser
        # l'identité visuelle de l'entreprise.
        try:
            from factures.models import _get_branding  # type: ignore
            branding = _get_branding()
        except Exception:
            branding = getattr(settings, "INVOICE_BRANDING", {}) or {}
            addr = branding.get("address", "")
            branding = {
                "name": branding.get("name", "Nettoyage Express"),
                "tagline": branding.get("tagline", "Espaces verts, nettoyage, peinture, bricolage"),
                "email": branding.get("email", ""),
                "phone": branding.get("phone", ""),
                "iban": branding.get("iban", ""),
                "bic": branding.get("bic", ""),
                "address_lines": [l.strip() for l in str(addr).splitlines() if l.strip()],
                "logo_path": branding.get("logo_path", None),
            }

        # Dessiner le bandeau d'en‑tête
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.HexColor("#0B5D46"))
        c.drawString(left_margin, y, "DEVIS")
        c.setFont("Helvetica", 10)
        y -= 8 * mm
        if branding.get("name"):
            c.drawString(left_margin, y, branding["name"])
            y -= 4 * mm
        if branding.get("tagline"):
            c.drawString(left_margin, y, branding["tagline"])
            y -= 4 * mm
        # Logo (facultatif)
        logo_path = branding.get("logo_path")
        if logo_path:
            try:
                from factures.models import _resolve_logo_path  # type: ignore
                resolved = _resolve_logo_path(logo_path)
                if resolved:
                    img = ImageReader(resolved)
                    iw, ih = img.getSize()
                    max_h = 20 * mm
                    w = max_h * (iw / ih)
                    c.drawImage(img, width - right_margin - w, height - top_margin + 5 * mm, width=w, height=max_h, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass

        # Coordonnées client
        y -= 6 * mm
        client = self.client
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left_margin, y, "Client :")
        y -= 5 * mm
        c.setFont("Helvetica", 10)
        c.drawString(left_margin, y, client.full_name)
        y -= 4 * mm
        c.drawString(left_margin, y, client.email)
        y -= 4 * mm
        c.drawString(left_margin, y, client.phone)
        if client.address_line:
            y -= 4 * mm
            c.drawString(left_margin, y, client.address_line)
        if client.city or client.zip_code:
            y -= 4 * mm
            city_line = f"{client.zip_code} {client.city}".strip()
            c.drawString(left_margin, y, city_line)

        # Numéro et date du devis
        y -= 10 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - right_margin, y, f"Devis n° {self.number}")
        y -= 5 * mm
        c.setFont("Helvetica", 10)
        c.drawRightString(width - right_margin, y, f"Date : {self.issue_date.strftime('%d/%m/%Y')}")
        if self.valid_until:
            y -= 4 * mm
            c.drawRightString(width - right_margin, y, f"Valable jusqu’au : {self.valid_until.strftime('%d/%m/%Y')}")

        # Tableau des items
        y -= 12 * mm
        table_start_y = y
        col_x = [left_margin, left_margin + 90*mm, left_margin + 110*mm, left_margin + 130*mm, left_margin + 150*mm]
        headers = ["Description", "Qté", "PU HT", "TVA %", "Total TTC"]
        c.setFillColor(colors.HexColor("#F5F7F9"))
        c.rect(left_margin, y - 6*mm, width - left_margin - right_margin, 6*mm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        for i, h in enumerate(headers):
            c.drawString(col_x[i] + 2, y - 5*mm, h)
        # Items
        y -= 7 * mm
        c.setFont("Helvetica", 9)
        for it in self.items:
            if y < bottom_margin + 40*mm:
                # Nouvelle page si nécessaire
                c.showPage()
                y = height - top_margin
                # Répétez l'en‑tête du tableau sur la nouvelle page
                c.setFillColor(colors.HexColor("#F5F7F9"))
                c.rect(left_margin, y - 6*mm, width - left_margin - right_margin, 6*mm, fill=1, stroke=0)
                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold", 9)
                for i, h in enumerate(headers):
                    c.drawString(col_x[i] + 2, y - 5*mm, h)
                y -= 7*mm
                c.setFont("Helvetica", 9)
            desc = it.description or (it.service.title if it.service else "")
            c.drawString(col_x[0] + 2, y - 5*mm, desc[:55])
            c.drawRightString(col_x[1] + 18, y - 5*mm, str(it.quantity))
            c.drawRightString(col_x[2] + 18, y - 5*mm, f"{it.unit_price:.2f} €")
            c.drawRightString(col_x[3] + 18, y - 5*mm, f"{it.tax_rate:.2f}")
            c.drawRightString(col_x[4] + 20, y - 5*mm, f"{it.total_ttc:.2f} €")
            y -= 5*mm

        # Récapitulatif des totaux
        y -= 5*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - right_margin - 60*mm, y, "Total HT :")
        c.drawRightString(width - right_margin, y, f"{self.total_ht:.2f} €")
        y -= 4*mm
        c.drawRightString(width - right_margin - 60*mm, y, "TVA :")
        c.drawRightString(width - right_margin, y, f"{self.tva:.2f} €")
        y -= 4*mm
        c.drawRightString(width - right_margin - 60*mm, y, "Total TTC :")
        c.drawRightString(width - right_margin, y, f"{self.total_ttc:.2f} €")

        # Encadré "Bon pour accord" et zone de signature
        #
        # Après les totaux, nous réservons un espace clairement délimité où
        # le client peut ajouter la mention manuscrite « Bon pour accord »
        # avant de signer.  Le cadre occupe toute la largeur disponible et
        # indique explicitement où écrire et signer.  En dessous du cadre,
        # une ligne est tracée pour la signature du client.
        from reportlab.lib.units import mm as _mm
        y -= 12 * mm
        box_height = 20 * mm
        box_width = width - left_margin - right_margin
        # Dessiner le rectangle délimitant la mention et la signature
        c.setStrokeColor(colors.HexColor("#C8C8C8"))
        c.setLineWidth(0.5)
        c.rect(left_margin, y - box_height, box_width, box_height, stroke=1, fill=0)
        # Texte à l'intérieur du cadre
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.black)
        c.drawString(left_margin + 2 * mm, y - 6 * mm, "Écrire \"Bon pour accord\" et signer :")
        c.setFont("Helvetica", 9)
        c.drawString(left_margin + 2 * mm, y - 11 * mm, "Date et signature du client")
        # Ligne pour la signature
        y = y - box_height - 8 * mm
        c.setStrokeColor(colors.HexColor("#000000"))
        c.setLineWidth(0.5)
        c.line(left_margin, y, left_margin + 80 * mm, y)
        c.setFont("Helvetica", 9)
        c.drawString(left_margin, y - 4 * mm, "Signature du client")

        # Pied de page
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#6B7280"))
        footer_y = bottom_margin
        if branding.get("address_lines"):
            for line in branding["address_lines"]:
                c.drawString(left_margin, footer_y, line)
                footer_y += 3.5*mm
        if branding.get("phone"):
            c.drawString(left_margin, footer_y, f"Tél : {branding['phone']}")
            footer_y += 3.5*mm
        if branding.get("email"):
            c.drawString(left_margin, footer_y, f"Email : {branding['email']}")

        c.save()
        pdf_bytes = buffer.getvalue()
        if attach:
            # Nom de fichier basé sur le numéro du devis
            filename = f"{self.number or 'devis'}.pdf"
            # Enregistrer le fichier dans le champ FileField
            self.pdf.save(filename, ContentFile(pdf_bytes), save=False)
            self.save(update_fields=["pdf"])
        return pdf_bytes


class QuoteItem(models.Model):
    """Une ligne de devis liée à un service ou à une description libre."""

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="quote_items")
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quote_items",
    )
    description = models.CharField(max_length=255, blank=True, help_text="Libellé si aucun service n'est associé.")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("20.00"),
        help_text="Taux de TVA en pourcentage (ex. 20.00 pour 20 %).",
    )

    class Meta:
        verbose_name = "ligne de devis"
        verbose_name_plural = "lignes de devis"

    def __str__(self) -> str:
        return self.description or (self.service.title if self.service else "Ligne")

    @property
    def total_ht(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_tva(self) -> Decimal:
        return (self.total_ht * self.tax_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_ttc(self) -> Decimal:
        return (self.total_ht + self.total_tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# -----------------------------------------------------------------------------
# Pièces jointes (photos) pour les devis
# -----------------------------------------------------------------------------

class QuotePhoto(models.Model):
    """Image ou document joint à un devis.

    Les clients peuvent fournir des photos de l'état initial avant les
    travaux.  Chaque fichier est relié à un devis via une clé étrangère.
    Les images sont stockées dans ``media/devis/photos``.
    """
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="devis/photos")

    class Meta:
        verbose_name = "photo du devis"
        verbose_name_plural = "photos du devis"

    def __str__(self) -> str:
        return f"Photo pour {self.quote.number}"
