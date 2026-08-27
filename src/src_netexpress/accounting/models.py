from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.file_validation import validate_document
from core.storage import private_storage


def supplier_upload_path(instance, filename):
    return f"accounting/suppliers/{timezone.now():%Y/%m}/{uuid4().hex}{Path(filename).suffix.lower()}"


class SupplierInvoice(models.Model):
    class Category(models.TextChoices):
        SUPPLIES = "supplies", "Produits et fournitures"
        EQUIPMENT = "equipment", "Matériel"
        SUBCONTRACTING = "subcontracting", "Sous-traitance"
        TRANSPORT = "transport", "Transport et déplacements"
        PREMISES = "premises", "Locaux et charges"
        SERVICES = "services", "Services et abonnements"
        OTHER = "other", "Autres"

    supplier_name = models.CharField("Fournisseur", max_length=200)
    supplier_key = models.CharField(max_length=200, editable=False)
    reference = models.CharField("Numéro de facture", max_length=100)
    issue_date = models.DateField("Date de facture", default=timezone.localdate, db_index=True)
    due_date = models.DateField("Échéance", null=True, blank=True)
    paid_on = models.DateField("Payée le", null=True, blank=True)
    total_ttc = models.DecimalField("Montant TTC (€)", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    vat_amount = models.DecimalField("TVA indiquée (€)", max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    category = models.CharField("Catégorie", max_length=30, choices=Category.choices, default=Category.OTHER)
    notes = models.TextField("Note pour le cabinet", blank=True, max_length=4000)
    file = models.FileField("Pièce justificative", upload_to=supplier_upload_path, storage=private_storage, validators=[validate_document])
    file_sha256 = models.CharField(max_length=64, unique=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="supplier_invoices")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_supplier_invoices")
    review_note = models.TextField(blank=True, max_length=2000)

    class Meta:
        ordering = ["-issue_date", "-pk"]
        verbose_name = "facture fournisseur"
        constraints = [
            models.UniqueConstraint(fields=["supplier_key", "reference"], name="unique_supplier_reference"),
            models.CheckConstraint(condition=models.Q(total_ttc__gt=0), name="supplier_positive_total"),
            models.CheckConstraint(condition=models.Q(vat_amount__gte=0) & models.Q(vat_amount__lte=models.F("total_ttc")), name="supplier_valid_vat"),
        ]

    @property
    def total_ht(self):
        return self.total_ttc - self.vat_amount

    @property
    def is_overdue(self):
        return bool(not self.paid_on and self.due_date and self.due_date < timezone.localdate())

    def clean(self):
        super().clean()
        self.supplier_key = " ".join(self.supplier_name.casefold().split())
        self.reference = self.reference.strip()
        if self.total_ttc is not None and self.vat_amount is not None and self.vat_amount > self.total_ttc:
            raise ValidationError({"vat_amount": "La TVA ne peut pas dépasser le TTC."})
        if self.issue_date and self.due_date and self.due_date < self.issue_date:
            raise ValidationError({"due_date": "L’échéance ne peut pas précéder la facture."})
        if self.paid_on and self.paid_on > timezone.localdate():
            raise ValidationError({"paid_on": "Une date de paiement ne peut pas être dans le futur."})

    def save(self, *args, **kwargs):
        self.supplier_key = " ".join(self.supplier_name.casefold().split())
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.supplier_name} — {self.reference}"


class InvoiceReview(models.Model):
    invoice = models.OneToOneField("factures.Invoice", on_delete=models.PROTECT, related_name="accounting_review")
    fingerprint = models.CharField(max_length=64)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True, max_length=2000)


class AccountingActivity(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "activité comptable"
