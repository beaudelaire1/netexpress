from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devis", "0006_quote_public_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="email_body_html",
            field=models.TextField(
                blank=True,
                help_text="Message personnalisé inséré dans l'email d'envoi du devis (HTML).",
            ),
        ),
    ]
