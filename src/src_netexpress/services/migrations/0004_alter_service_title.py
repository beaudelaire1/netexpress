from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0003_remove_service_base_price_service_unit_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="title",
            field=models.CharField(max_length=200),
        ),
    ]
