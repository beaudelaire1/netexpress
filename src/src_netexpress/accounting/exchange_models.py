from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.file_validation import validate_document
from core.storage import private_storage


def exchange_document_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"accounting/exchanges/{timezone.now():%Y/%m}/{uuid4().hex}{suffix}"


class AccountingExchange(models.Model):
    class Kind(models.TextChoices):
        QUESTION = "question", "Question"
        DOCUMENT_REQUEST = "document_request", "Pièce demandée"
        CORRECTION_REQUEST = "correction_request", "Correction demandée"
        INFORMATION = "information", "Information"
        DOCUMENT_DELIVERY = "document_delivery", "Document transmis"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        OPEN = "open", "Ouvert"
        WAITING_NETEXPRESS = "waiting_netexpress", "En attente de NetExpress"
        WAITING_ACCOUNTANT = "waiting_accountant", "En attente du cabinet"
        RESOLVED = "resolved", "Résolu"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normale"
        HIGH = "high", "Haute"

    subject = models.CharField("Sujet", max_length=200)
    kind = models.CharField("Type", max_length=30, choices=Kind.choices, default=Kind.QUESTION)
    status = models.CharField("Statut", max_length=30, choices=Status.choices, default=Status.OPEN, db_index=True)
    priority = models.CharField("Priorité", max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_accounting_exchanges",
    )
    invoice = models.ForeignKey(
        "factures.Invoice",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accounting_exchanges",
    )
    quote = models.ForeignKey(
        "devis.Quote",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accounting_exchanges",
    )
    supplier_invoice = models.ForeignKey(
        "accounting.SupplierInvoice",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accounting_exchanges",
    )
    accounting_document = models.ForeignKey(
        "accounting.AccountingDocument",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accounting_exchanges",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-last_activity_at", "-pk"]
        verbose_name = "échange comptable"
        verbose_name_plural = "échanges comptables"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        invoice__isnull=True,
                        quote__isnull=True,
                        supplier_invoice__isnull=True,
                        accounting_document__isnull=True,
                    )
                    | models.Q(
                        invoice__isnull=False,
                        quote__isnull=True,
                        supplier_invoice__isnull=True,
                        accounting_document__isnull=True,
                    )
                    | models.Q(
                        invoice__isnull=True,
                        quote__isnull=False,
                        supplier_invoice__isnull=True,
                        accounting_document__isnull=True,
                    )
                    | models.Q(
                        invoice__isnull=True,
                        quote__isnull=True,
                        supplier_invoice__isnull=False,
                        accounting_document__isnull=True,
                    )
                    | models.Q(
                        invoice__isnull=True,
                        quote__isnull=True,
                        supplier_invoice__isnull=True,
                        accounting_document__isnull=False,
                    )
                ),
                name="accounting_exchange_single_context",
            )
        ]

    def clean(self):
        super().clean()
        context_count = sum(
            bool(value)
            for value in (
                self.invoice_id,
                self.quote_id,
                self.supplier_invoice_id,
                self.accounting_document_id,
            )
        )
        if context_count > 1:
            raise ValidationError(
                "Un échange comptable ne peut être lié qu'à une seule pièce de contexte."
            )
        self.subject = (self.subject or "").strip()
        if not self.subject:
            raise ValidationError({"subject": "Le sujet de l'échange est obligatoire."})

    def __str__(self):
        return self.subject


class AccountingExchangeMessage(models.Model):
    exchange = models.ForeignKey(
        AccountingExchange,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="accounting_exchange_messages",
    )
    content = models.TextField("Message", max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        verbose_name = "message d'échange comptable"

    def clean(self):
        super().clean()
        self.content = (self.content or "").strip()
        if not self.content:
            raise ValidationError({"content": "Le message ne peut pas être vide."})

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        AccountingExchange.objects.filter(
            pk=self.exchange_id,
            last_activity_at__lt=self.created_at,
        ).update(last_activity_at=self.created_at)
        return result


class AccountingExchangeDocument(models.Model):
    class Type(models.TextChoices):
        ACCOUNTANT_NOTE = "accountant_note", "Note du cabinet"
        CORRECTION = "correction", "Document corrigé"
        SUPPORTING_DOCUMENT = "supporting_document", "Justificatif"
        SPREADSHEET = "spreadsheet", "Tableau de travail"
        LETTER = "letter", "Courrier"
        OTHER = "other", "Autre document"

    class Visibility(models.TextChoices):
        SHARED = "shared", "Partagé"
        NETEXPRESS_ONLY = "netexpress_only", "Interne NetExpress"

    exchange = models.ForeignKey(
        AccountingExchange,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    message = models.ForeignKey(
        AccountingExchangeMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="accounting_exchange_documents",
    )
    title = models.CharField("Titre", max_length=200)
    document_type = models.CharField("Type", max_length=30, choices=Type.choices, default=Type.OTHER)
    visibility = models.CharField(
        "Visibilité",
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.SHARED,
        db_index=True,
    )
    file = models.FileField(
        "Document",
        upload_to=exchange_document_upload_path,
        storage=private_storage,
        validators=[validate_document],
    )
    original_filename = models.CharField(max_length=255, blank=True, editable=False)
    file_sha256 = models.CharField(max_length=64, blank=True, editable=False, db_index=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    mime_type = models.CharField(max_length=120, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "document d'échange comptable"
        constraints = [
            models.UniqueConstraint(
                fields=["file_sha256"],
                condition=~models.Q(file_sha256=""),
                name="unique_accounting_exchange_document_hash",
            )
        ]

    def clean(self):
        super().clean()
        if self.message_id and self.message.exchange_id != self.exchange_id:
            raise ValidationError(
                {"message": "Le message et le document doivent appartenir au même échange."}
            )
        self.title = (self.title or "").strip()
        if not self.title:
            raise ValidationError({"title": "Le titre du document est obligatoire."})

    def _capture_file_metadata(self):
        if not self.file:
            return

        if not self.original_filename:
            self.original_filename = Path(self.file.name).name[:255]

        try:
            self.file_size = self.file.size
        except (OSError, ValueError):
            pass

        wrapped = getattr(self.file, "file", None)
        content_type = getattr(wrapped, "content_type", "")
        if content_type and not self.mime_type:
            self.mime_type = str(content_type)[:120]

        if self.file_sha256:
            return

        digest = hashlib.sha256()
        try:
            for chunk in self.file.chunks():
                digest.update(chunk)
            self.file.seek(0)
        except (AttributeError, OSError, ValueError):
            return
        self.file_sha256 = digest.hexdigest()

    def save(self, *args, **kwargs):
        self._capture_file_metadata()
        result = super().save(*args, **kwargs)
        AccountingExchange.objects.filter(
            pk=self.exchange_id,
            last_activity_at__lt=self.created_at,
        ).update(last_activity_at=self.created_at)
        return result

    def __str__(self):
        return self.title


class AccountingExchangeReadState(models.Model):
    exchange = models.ForeignKey(
        AccountingExchange,
        on_delete=models.CASCADE,
        related_name="read_states",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounting_exchange_read_states",
    )
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "état de lecture d'un échange comptable"
        constraints = [
            models.UniqueConstraint(
                fields=["exchange", "user"],
                name="unique_accounting_exchange_read_state",
            )
        ]
