# Collaboration workspace completion after the domain foundation migration.

import accounting.exchange_file_validation
import accounting.exchange_models
import core.storage
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0003_accounting_exchange_domain"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountingexchangedocument",
            name="promoted_to",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_exchange_document",
                to="accounting.accountingdocument",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="accountingexchangedocument",
            name="unique_accounting_exchange_document_hash",
        ),
        migrations.AddConstraint(
            model_name="accountingexchangedocument",
            constraint=models.UniqueConstraint(
                condition=models.Q(("file_sha256", ""), _negated=True),
                fields=("exchange", "file_sha256"),
                name="unique_exchange_document_hash_per_thread",
            ),
        ),
        migrations.AlterField(
            model_name="accountingexchangedocument",
            name="file",
            field=models.FileField(
                storage=core.storage.PrivateStorage(),
                upload_to=accounting.exchange_models.exchange_document_upload_path,
                validators=[accounting.exchange_file_validation.validate_exchange_document],
                verbose_name="Document",
            ),
        ),
    ]
