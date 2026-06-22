from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_profile_accounts_pr_role_fae1f3_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="email_verified",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "L'adresse e-mail a été confirmée (requis pour l'accès aux "
                    "documents pour les comptes auto-inscrits)."
                ),
            ),
        ),
    ]
