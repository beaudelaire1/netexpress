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
from django.utils.translation import gettext_lazy as _
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
        verbose_name = _("client")
        verbose_name_plural = _("clients")

    def __str__(self) -> str:
        return self.full_name


class QuoteRequestPhoto(models.Model):
    """Fichier (photo ou document) joint à une demande de devis."""

    image = models.ImageField(_("Fichier"), upload_to="devis/requests/photos")

    class Meta:
        verbose_name = _("photo de demande de devis")
        verbose_name_plural = _("photos de demandes de devis")

    def __str__(self) -> str:
        return self.image.name if self.image else "Pièce jointe"


class QuoteRequest(models.Model):
    """Demande initiale envoyée par un client depuis le site ou l'interface publique."""

    class QuoteRequestStatus(models.TextChoices):
        NEW = "new", _("Nouveau")
        PROCESSED = "processed", _("Traité")
        REJECTED = "rejected", _("Rejeté")

    client_name = models.CharField(_("Nom du client"), max_length=200)
    email = models.EmailField(_("Email"))
    phone = models.CharField(_("Téléphone"), max_length=50)
    address = models.CharField(_("Adresse"), max_length=255)
    message = models.TextField(_("Message"), blank=True)
    preferred_date = models.DateField(_("Date souhaitée"), null=True, blank=True)
    status = models.CharField(
        _("Statut"),
        max_length=20,
        choices=QuoteRequestStatus.choices,
        default=QuoteRequestStatus.NEW,
    )
    photos = models.ManyToManyField(
        "devis.QuoteRequestPhoto",
        verbose_name=_("Photos"),
        blank=True,
        related_name="quote_requests",
    )
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("demande de devis")
        verbose_name_plural = _("demandes de devis")

    def __str__(self) -> str:
        return f"Demande {self.id} - {self.client_name}"



class Quote(models.Model):
    """Demande de devis.

    Un numéro de devis est généré automatiquement à partir de l'année et de
    l'identifiant.  Le champ ``service`` est optionnel pour permettre des
    demandes libres.  Le statut permet de suivre l'avancement (brouillon,
    envoyé, accepté, rejeté).  Les totaux permettent d'anticiper la facture.
    """

    class QuoteStatus(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        SENT = "sent", _("Envoyé")
        ACCEPTED = "accepted", _("Accepté")
        REJECTED = "rejected", _("Refusé")
        INVOICED = "invoiced", _("Facturé")


    number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Numéro de devis format DEV-AAAA-XXX, généré automatiquement."
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="quotes")
    quote_request = models.ForeignKey(
        "QuoteRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
        help_text="Demande d'origine (facultative).",
    )
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
    status = models.CharField(max_length=20, choices=QuoteStatus.choices, default=QuoteStatus.DRAFT)
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

        Implémentation Django "Service Layer" simple (sans couche hexagonale).
        """
        from decimal import Decimal

        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")

        # quote.items related_name expected
        for item in self.quote_items.all():
            qty = Decimal(str(getattr(item, "quantity", 0) or 0))
            unit = Decimal(str(getattr(item, "unit_price", 0) or 0))
            rate = Decimal(str(getattr(item, "tax_rate", 0) or 0))
            line_ht = qty * unit
            line_tva = (line_ht * rate) / Decimal("100")
            total_ht += line_ht
            total_tva += line_tva

        self.total_ht = total_ht
        self.tva = total_tva
        self.total_ttc = total_ht + total_tva
        self.save(update_fields=["total_ht", "tva", "total_ttc"])

    def generate_pdf(self, attach: bool = True) -> bytes:
        """
        Génère un document PDF décrivant ce devis via WeasyPrint.

        Délègue la génération au service unifié QuotePdfService qui utilise
        des templates HTML/CSS pour un rendu professionnel et facilement
        personnalisable.

        :param attach: si vrai, le fichier est rattaché au modèle
        :return: le contenu binaire du PDF généré
        :raises RuntimeError: si WeasyPrint n'est pas installé
        """
        from core.services.pdf_service import QuotePdfService
        from django.core.files.base import ContentFile

        service = QuotePdfService()
        pdf_file = service.generate(self)

        if attach:
            self.pdf.save(pdf_file.filename, ContentFile(pdf_file.content), save=True)

        return pdf_file.content

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
    description = models.CharField(
        _("Description"),
        max_length=255,
        help_text=_("Libellé de la ligne (prérempli si un service est sélectionné)."),
    )
    quantity = models.DecimalField(
        _("Quantité"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
    )
    unit_price = models.DecimalField(
        _("Prix unitaire HT"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    tax_rate = models.DecimalField(
        _("Taux de TVA"),
        max_digits=4,
        decimal_places=2,
        default=Decimal("20.00"),
        help_text=_("Taux de TVA en pourcentage (ex. 20.00 pour 20 %)."),
    )

    class Meta:
        verbose_name = _("ligne de devis")
        verbose_name_plural = _("lignes de devis")

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
        verbose_name = _("photo du devis")
        verbose_name_plural = _("photos du devis")

    def __str__(self) -> str:
        return f"Photo pour {self.quote.number}"

# === Signaux: notifications devis (PDF + e‑mails) ===
import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.services.email_service import PremiumEmailService

logger = logging.getLogger(__name__)


def _guess_quote_email(quote):
    """Détecte de manière défensive l'email de contact client."""
    for attr in ("email", "client_email", "contact_email"):
        value = getattr(quote, attr, None)
        if value:
            return value
    client = getattr(quote, "client", None)
    if client is not None:
        for attr in ("email", "contact_email"):
            value = getattr(client, attr, None)
            if value:
                return value
    return None


@receiver(post_save, sender=Quote)
def send_quote_created_email(sender, instance: "Quote", created: bool, **kwargs):
    """Envoi des notifications lorsqu'un devis est créé.

    Objectif: garantir un envoi **réel** (pas de Celery obligatoire) et
    une génération PDF **avant** l'envoi au client.
    """
    if not created:
        return

    logger.info("Nouveau devis créé: %s (client: %s)", instance.number, instance.client)

    # Calcul des totaux avec logging des erreurs
    try:
        instance.compute_totals()
        logger.debug("Totaux calculés pour devis %s: HT=%s, TTC=%s",
                    instance.number, instance.total_ht, instance.total_ttc)
    except Exception as e:
        logger.exception("Échec compute_totals pour devis %s: %s", instance.pk, e)
        # On continue quand même pour notifier l'admin

    email_service = PremiumEmailService()

    # Notification admin (ne bloque jamais l'envoi client)
    try:
        email_service.notify_admin_quote_created(instance)
        logger.info("Notification admin envoyée pour devis %s", instance.number)
    except Exception as e:
        logger.warning("Échec notification admin pour devis %s: %s", instance.pk, e)

    # Email client avec PDF
    acceptance_url = None
    site_url = getattr(settings, "SITE_URL", None)
    token = getattr(instance, "accept_token", None)
    if site_url and token:
        acceptance_url = site_url.rstrip("/") + f"/devis/accepter/{token}/"

    try:
        email_service.send_quote_pdf_to_client(instance, acceptance_url=acceptance_url)
        logger.info("Email devis %s envoyé au client %s",
                   instance.number, _guess_quote_email(instance))
    except Exception as e:
        logger.exception("Échec envoi email client pour devis %s: %s", instance.pk, e)
