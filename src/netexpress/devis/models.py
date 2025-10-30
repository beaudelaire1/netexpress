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
présentation a été améliorée via des visuels issus d'Unsplash.  Les modèles
restent compatibles avec l'interface d'administration et les actions de
génération de factures.
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
        help_text="Numéro de devis format NE-AAAA-####, généré automatiquement."
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

    def __str__(self) -> str:
        return f"Devis {self.number or ''} pour {self.client.full_name}"

    def save(self, *args, **kwargs):
        # Attribution d'un numéro de devis si nécessaire : NE-AAAA-####
        if not self.number:
            # l'année est celle de la date d'émission
            year = self.issue_date.year if hasattr(self, "issue_date") and self.issue_date else self.created_at.year
            prefix = f"NE-{year}-"
            last_number = Quote.objects.filter(number__startswith=prefix).order_by("number").last()
            if last_number:
                # extraire le compteur
                try:
                    last_counter = int(last_number.number.split("-")[-1])
                except ValueError:
                    last_counter = 0
            else:
                last_counter = 0
            self.number = f"{prefix}{last_counter + 1:04d}"
        super().save(*args, **kwargs)

    @property
    def items(self) -> List["QuoteItem"]:
        return self.quote_items.all()

    def compute_totals(self):
        """Calcule et met à jour les totaux HT, TVA et TTC à partir des items."""
        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")
        for item in self.items:
            total_ht += item.total_ht
            total_tva += item.total_tva
        self.total_ht = total_ht.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.tva = total_tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.total_ttc = (self.total_ht + self.tva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.save()


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
