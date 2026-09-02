"""Reprend le client du devis sur les factures déjà émises.

Le champ ``Invoice.client`` devient la source unique de vérité pour savoir qui
est facturé. Les factures historiques n'ont que leur devis : on recopie donc
``quote.client`` afin que l'affichage, les emails et la comptabilité continuent
de fonctionner sans passer par la jointure.
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery


def backfill_client(apps, schema_editor):
    Invoice = apps.get_model("factures", "Invoice")
    Quote = apps.get_model("devis", "Quote")
    Invoice.objects.filter(client__isnull=True, quote__isnull=False).update(
        client_id=Subquery(
            Quote.objects.filter(pk=OuterRef("quote_id")).values("client_id")[:1]
        )
    )


def unset_client(apps, schema_editor):
    Invoice = apps.get_model("factures", "Invoice")
    Invoice.objects.update(client=None)


class Migration(migrations.Migration):

    dependencies = [
        ("factures", "0010_invoice_client_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_client, unset_client),
    ]
