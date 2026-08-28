# Generated manually for the accounting collaboration domain.

import accounting.exchange_file_validation
import accounting.exchange_models
import core.storage
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0002_simplify_deposits_and_documents"),
        ("devis", "0010_alter_quote_pdf_alter_quotephoto_image_and_more"),
        ("factures", "0009_invoice_is_credit_note_invoice_issued_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountingExchange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=200, verbose_name="Sujet")),
                ("kind", models.CharField(choices=[("question", "Question"), ("document_request", "Pièce demandée"), ("correction_request", "Correction demandée"), ("information", "Information"), ("document_delivery", "Document transmis"), ("other", "Autre")], default="question", max_length=30, verbose_name="Type")),
                ("status", models.CharField(choices=[("open", "Ouvert"), ("waiting_netexpress", "En attente de NetExpress"), ("waiting_accountant", "En attente du cabinet"), ("resolved", "Résolu")], db_index=True, default="open", max_length=30, verbose_name="Statut")),
                ("priority", models.CharField(choices=[("normal", "Normale"), ("high", "Haute")], default="normal", max_length=10, verbose_name="Priorité")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_activity_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("accounting_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="accounting_exchanges", to="accounting.accountingdocument")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_accounting_exchanges", to=settings.AUTH_USER_MODEL)),
                ("invoice", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="accounting_exchanges", to="factures.invoice")),
                ("quote", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="accounting_exchanges", to="devis.quote")),
                ("supplier_invoice", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="accounting_exchanges", to="accounting.supplierinvoice")),
            ],
            options={
                "verbose_name": "échange comptable",
                "verbose_name_plural": "échanges comptables",
                "ordering": ["-last_activity_at", "-pk"],
            },
        ),
        migrations.AddConstraint(
            model_name="accountingexchange",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(accounting_document__isnull=True, invoice__isnull=True, quote__isnull=True, supplier_invoice__isnull=True)
                    | models.Q(accounting_document__isnull=True, invoice__isnull=False, quote__isnull=True, supplier_invoice__isnull=True)
                    | models.Q(accounting_document__isnull=True, invoice__isnull=True, quote__isnull=False, supplier_invoice__isnull=True)
                    | models.Q(accounting_document__isnull=True, invoice__isnull=True, quote__isnull=True, supplier_invoice__isnull=False)
                    | models.Q(accounting_document__isnull=False, invoice__isnull=True, quote__isnull=True, supplier_invoice__isnull=True)
                ),
                name="accounting_exchange_single_context",
            ),
        ),
        migrations.CreateModel(
            name="AccountingExchangeMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField(max_length=4000, verbose_name="Message")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accounting_exchange_messages", to=settings.AUTH_USER_MODEL)),
                ("exchange", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="accounting.accountingexchange")),
            ],
            options={
                "verbose_name": "message d'échange comptable",
                "ordering": ["created_at", "pk"],
            },
        ),
        migrations.CreateModel(
            name="AccountingExchangeDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="Titre")),
                ("document_type", models.CharField(choices=[("accountant_note", "Note du cabinet"), ("correction", "Document corrigé"), ("supporting_document", "Justificatif"), ("spreadsheet", "Tableau de travail"), ("letter", "Courrier"), ("other", "Autre document")], default="other", max_length=30, verbose_name="Type")),
                ("visibility", models.CharField(choices=[("shared", "Partagé"), ("netexpress_only", "Interne NetExpress")], db_index=True, default="shared", max_length=20, verbose_name="Visibilité")),
                ("file", models.FileField(storage=core.storage.PrivateStorage(), upload_to=accounting.exchange_models.exchange_document_upload_path, validators=[accounting.exchange_file_validation.validate_exchange_document], verbose_name="Document")),
                ("original_filename", models.CharField(blank=True, editable=False, max_length=255)),
                ("file_sha256", models.CharField(blank=True, db_index=True, editable=False, max_length=64)),
                ("file_size", models.PositiveBigIntegerField(blank=True, editable=False, null=True)),
                ("mime_type", models.CharField(blank=True, editable=False, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("exchange", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="accounting.accountingexchange")),
                ("message", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="documents", to="accounting.accountingexchangemessage")),
                ("promoted_to", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_exchange_document", to="accounting.accountingdocument")),
                ("uploaded_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accounting_exchange_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "document d'échange comptable",
                "ordering": ["-created_at", "-pk"],
            },
        ),
        migrations.AddConstraint(
            model_name="accountingexchangedocument",
            constraint=models.UniqueConstraint(condition=models.Q(("file_sha256", ""), _negated=True), fields=("exchange", "file_sha256"), name="unique_exchange_document_hash_per_thread"),
        ),
        migrations.CreateModel(
            name="AccountingExchangeReadState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_read_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("exchange", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="read_states", to="accounting.accountingexchange")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accounting_exchange_read_states", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "état de lecture d'un échange comptable",
            },
        ),
        migrations.AddConstraint(
            model_name="accountingexchangereadstate",
            constraint=models.UniqueConstraint(fields=("exchange", "user"), name="unique_accounting_exchange_read_state"),
        ),
    ]
